#!/usr/bin/env python3
"""Paper-only XAUUSD hybrid signal prototype. No broker or trading APIs."""
from __future__ import annotations

import argparse, csv, json, math, os, random, statistics, sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

@dataclass(frozen=True)
class Candle:
    time: str; open: float; high: float; low: float; close: float; volume: float = 0.0

@dataclass
class Signal:
    side: str; index: int; entry: float; stop: float; target: float; atr: float; score: float = 1.0; reason: str = ""

def load_csv(path: str) -> list[Candle]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        needed = {"time", "open", "high", "low", "close"}
        if not reader.fieldnames or not needed.issubset(set(reader.fieldnames)):
            raise ValueError("CSV needs header: time,open,high,low,close[,volume]")
        rows = [Candle(r["time"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r.get("volume") or 0)) for r in reader]
    if len(rows) < 80: raise ValueError("Need at least 80 candles")
    return rows

def demo_data(n=900, seed=7) -> list[Candle]:
    rng, price, out = random.Random(seed), 2300.0, []
    t = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        drift = 0.20 * math.sin(i / 90) + (0.10 if i % 170 < 85 else -0.07)
        op = price; close = op + drift + rng.gauss(0, 2.5)
        high = max(op, close) + abs(rng.gauss(1.1, .7)); low = min(op, close) - abs(rng.gauss(1.1, .7))
        out.append(Candle((t + timedelta(minutes=5*i)).isoformat(), op, high, low, close, rng.randint(80, 500)))
        price = close
    return out

def fetch_twelve_data(api_keys: str, symbol="XAU/USD", interval="5min", outputsize=200) -> list[Candle]:
    """Fetch OHLC candles with quota/error failover; API keys never appear in errors."""
    keys = [k.strip() for k in api_keys.split(",") if k.strip()]
    if not keys: raise ValueError("TWELVE_DATA_API_KEYS is required for Twelve Data mode")
    last_error = "no response"
    for key in keys:
        query = urlencode({"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": key})
        try:
            req = Request("https://api.twelvedata.com/time_series?" + query, headers={"User-Agent": "xauusd-paper-signal-bot/1.0"})
            with urlopen(req, timeout=15) as response: payload = json.load(response)
            values = payload.get("values")
            if not values: raise ValueError(payload.get("message", payload.get("status", "no candle data")))
            rows = [Candle(str(x["datetime"]), float(x["open"]), float(x["high"]), float(x["low"]), float(x["close"]), float(x.get("volume") or 0)) for x in values]
            rows.sort(key=lambda x: x.time)
            if len(rows) < 80: raise ValueError("provider returned fewer than 80 candles")
            return rows
        except Exception as exc:
            last_error = type(exc).__name__ + ": " + str(exc)
    raise RuntimeError("All Twelve Data keys failed: " + last_error)

def ema(values, period):
    out, alpha = [], 2/(period+1); v = values[0]
    for x in values: v = alpha*x + (1-alpha)*v; out.append(v)
    return out

def indicators(c):
    closes=[x.close for x in c]; e20, e50=ema(closes,20), ema(closes,50)
    trs=[c[0].high-c[0].low] + [max(x.high-x.low, abs(x.high-p.close), abs(x.low-p.close)) for p,x in zip(c,c[1:])]
    atr=[]
    for i in range(len(c)): atr.append(statistics.fmean(trs[max(0,i-13):i+1]))
    rsi=[]
    for i in range(len(c)):
        diffs=[closes[j]-closes[j-1] for j in range(max(1,i-13),i+1)]
        gain=statistics.fmean([max(x,0) for x in diffs]) if diffs else 0; loss=statistics.fmean([max(-x,0) for x in diffs]) if diffs else 0
        rsi.append(100 if loss == 0 and gain else (50 if not loss else 100-100/(1+gain/loss)))
    return e20,e50,atr,rsi

def candidate(c, i, ind) -> Signal | None:
    if i < 55: return None
    e20,e50,atr,rsi=ind; x=c[i]; prior=c[i-20:i]
    lo,hi=min(z.low for z in prior),max(z.high for z in prior)
    bull_sweep=x.low < lo and x.close > lo; bear_sweep=x.high > hi and x.close < hi
    bull=e20[i]>e50[i] and bull_sweep and rsi[i] > 45
    bear=e20[i]<e50[i] and bear_sweep and rsi[i] < 55
    if not (bull or bear) or atr[i] <= 0: return None
    side="BUY" if bull else "SELL"; risk=1.2*atr[i]
    stop=x.close-risk if bull else x.close+risk; target=x.close+2*risk if bull else x.close-2*risk
    return Signal(side,i,x.close,stop,target,atr[i],reason=f"EMA trend + liquidity sweep + RSI {rsi[i]:.1f}; ATR {atr[i]:.2f}")

class LogisticRanker:
    def fit(self, samples, labels):
        if len(samples)<10 or len(set(labels))<2: self.ready=False; return self
        self.mean=[statistics.fmean(row[j] for row in samples) for j in range(len(samples[0]))]
        self.scale=[max(1e-8, statistics.pstdev(row[j] for row in samples)) for j in range(len(samples[0]))]
        self.w=[0.0]*(len(self.mean)+1)
        for _ in range(300):
            grad=[0.0]*len(self.w)
            for row,y in zip(samples,labels):
                z=self.w[0]+sum(w*((v-m)/s) for w,v,m,s in zip(self.w[1:],row,self.mean,self.scale)); p=1/(1+math.exp(-max(-30,min(30,z))))
                grad[0]+=p-y
                for j,(v,m,s) in enumerate(zip(row,self.mean,self.scale)): grad[j+1]+=(p-y)*(v-m)/s
            for j in range(len(self.w)): self.w[j]-=.08*grad[j]/len(samples)
        self.ready=True; return self
    def predict(self,row):
        if not getattr(self,"ready",False): return 1.0
        z=self.w[0]+sum(w*((v-m)/s) for w,v,m,s in zip(self.w[1:],row,self.mean,self.scale))
        return 1/(1+math.exp(-max(-30,min(30,z))))

def features(c, i, ind):
    e20,e50,atr,rsi=ind
    return [(e20[i]-e50[i])/max(atr[i],1e-8), rsi[i]/100, (c[i].high-c[i].low)/max(atr[i],1e-8), c[i].volume]

def outcome(c, s, horizon=12):
    for x in c[s.index+1:min(len(c),s.index+1+horizon)]:
        if s.side=="BUY":
            if x.low <= s.stop: return 0
            if x.high >= s.target: return 1
        else:
            if x.high >= s.stop: return 0
            if x.low <= s.target: return 1
    return 0

def alerts(c, start, end, use_ml=False):
    ind=indicators(c); split=max(80,start)
    ranker=LogisticRanker()
    if use_ml:
        train=[]
        for i in range(55,split):
            s=candidate(c,i,ind)
            if s and i+12 < split: train.append((features(c,i,ind),outcome(c,s)))
        ranker.fit([x for x,_ in train],[y for _,y in train])
    active=None; events=[]
    for i in range(start,end):
        x=c[i]
        if active:
            exit_price=reason=None
            if active.side=="BUY" and x.low<=active.stop: exit_price,reason=active.stop,"stop loss"
            elif active.side=="SELL" and x.high>=active.stop: exit_price,reason=active.stop,"stop loss"
            elif active.side=="BUY" and x.high>=active.target: exit_price,reason=active.target,"take profit"
            elif active.side=="SELL" and x.low<=active.target: exit_price,reason=active.target,"take profit"
            elif (active.side=="BUY" and ind[0][i]<ind[1][i]) or (active.side=="SELL" and ind[0][i]>ind[1][i]): exit_price,reason=x.close,"trend reversal"
            if reason:
                pnl=(exit_price-active.entry)*(1 if active.side=="BUY" else -1)
                events.append(("CLOSE",i,active,exit_price,reason,pnl)); active=None
        if not active:
            s=candidate(c,i,ind)
            if s:
                s.score=ranker.predict(features(c,i,ind)) if use_ml else 1.0
                if s.score >= .50: events.append((s.side,i,s,None,"entry",None)); active=s
    return events, getattr(ranker,"ready",False)

def format_event(event,c):
    kind,i,s,price,reason,pnl=event
    if kind=="CLOSE": return f"XAUUSD CLOSE {s.side} | exit {price:.2f} | P/L {pnl:+.2f} | {reason} | {c[i].time}"
    return f"XAUUSD {kind} | entry {s.entry:.2f} | SL {s.stop:.2f} | TP {s.target:.2f} | score {s.score:.2f} | {s.reason} | {c[i].time}"

def notify(message, telegram=False):
    if not telegram: print("[DRY-RUN]",message); return
    token,chat=os.getenv("TELEGRAM_BOT_TOKEN"),os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required for --telegram")
    if not chat.startswith("-"): raise RuntimeError("TELEGRAM_CHAT_ID must be a negative group or supergroup ID; private chats are blocked")
    req=Request(f"https://api.telegram.org/bot{token}/sendMessage", data=urlencode({"chat_id":chat,"text":message}).encode(), method="POST")
    with urlopen(req,timeout=10) as response:
        if not json.load(response).get("ok"): raise RuntimeError("Telegram rejected the message")

def report(events):
    closed=[x for x in events if x[0]=="CLOSE"]; pnl=[x[5] for x in closed]
    wins=sum(x>0 for x in pnl); losses=sum(x<=0 for x in pnl)
    return {"entries":sum(x[0] in {"BUY","SELL"} for x in events),"closed_trades":len(closed),"wins":wins,"losses":losses,"win_rate":None if not pnl else round(100*wins/len(pnl),2),"net_price_units":round(sum(pnl),2)}

def main():
    p=argparse.ArgumentParser(description="Paper-only XAUUSD signal prototype")
    p.add_argument("command",choices=["backtest","simulate"]); p.add_argument("--csv"); p.add_argument("--demo",action="store_true"); p.add_argument("--ml",action="store_true"); p.add_argument("--telegram",action="store_true"); p.add_argument("--dry-run",action="store_true")
    a=p.parse_args()
    if not a.csv and not a.demo: p.error("choose --csv PATH or --demo")
    c=demo_data() if a.demo else load_csv(a.csv)
    start=int(len(c)*.70); events, ml_ready=alerts(c,start,len(c),a.ml)
    if a.command=="simulate":
        for e in events: notify(format_event(e,c), a.telegram and not a.dry_run)
        if not events: notify(f"XAUUSD WAIT | no qualifying setup in {c[start].time} to {c[-1].time}",a.telegram and not a.dry_run)
    result=report(events); result.update({"data":"demo (synthetic)" if a.demo else str(a.csv),"test_candles":len(c)-start,"ml_enabled":a.ml,"ml_trained":ml_ready})
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
