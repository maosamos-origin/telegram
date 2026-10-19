#!/usr/bin/env python3
"""Hardened paper-only HTTP monitor. Run one worker instance; no broker actions."""
import json
import os
import hmac
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bot
from alert_templates import render, STYLES
from signal_history import SignalHistory

SCAN_SECONDS = max(60, int(os.getenv('PAPER_SCAN_INTERVAL_SECONDS', '300')))
DATA_MODE = os.getenv('PAPER_DATA_MODE', 'demo').lower()
TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
TEMPLATE_STYLE = os.getenv('TELEGRAM_TEMPLATE', 'premium').lower()
STATE_FILE = Path(os.getenv('ALERT_STATE_FILE', './alert-state.json'))
MAX_STALE_SECONDS = max(60, int(os.getenv('MAX_CANDLE_STALE_SECONDS', '1200')))
TWELVE_INTERVAL = os.getenv('TWELVE_DATA_INTERVAL', '5min')
TWELVE_SYMBOL = os.getenv('TWELVE_DATA_SYMBOL', 'XAU/USD')
HISTORY_DB = Path(os.getenv('SIGNAL_HISTORY_DB', './signal-history.db'))
lock = threading.Lock()
state = {'mode':'paper', 'data_mode':DATA_MODE, 'telegram_delivery':'enabled' if TELEGRAM_ENABLED else 'disabled',
         'template':TEMPLATE_STYLE,'last_scan':None,'last_result':None,'error':None}

def _load_delivery():
    try:
        loaded = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        return set(loaded.get('sent', []))
    except (OSError, ValueError, TypeError):
        return set()

sent_events = _load_delivery()

def _persist_sent():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps({'sent': sorted(sent_events)[-5000:]}), encoding='utf-8')
    tmp.replace(STATE_FILE)

def _parse_time(s):
    normalized = s.replace('Z', '+00:00')
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        # Twelve Data timestamps have no guaranteed UTC offset: fail closed
        # unless user explicitly specifies the source timezone as UTC.
        if os.getenv('MARKET_DATA_TIMEZONE', '') != 'UTC':
            raise ValueError('Candle timestamp lacks timezone; set MARKET_DATA_TIMEZONE=UTC only if provider timestamps are UTC')
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def scan_once():
    if TEMPLATE_STYLE not in STYLES: raise ValueError('Invalid TELEGRAM_TEMPLATE')
    if DATA_MODE == 'demo':
        candles = bot.demo_data()
    elif DATA_MODE == 'csv':
        candles = bot.load_csv(os.getenv('XAUUSD_CSV_PATH',''))
    elif DATA_MODE == 'twelve_data':
        candles = bot.fetch_twelve_data(os.getenv('TWELVE_DATA_API_KEYS',''), TWELVE_SYMBOL,
                                        TWELVE_INTERVAL, max(80,int(os.getenv('TWELVE_DATA_OUTPUTSIZE','200'))))
    else:
        raise ValueError('PAPER_DATA_MODE must be demo, csv, or twelve_data')
    if len(candles) < 80: raise ValueError('Insufficient candles')
    if TELEGRAM_ENABLED and DATA_MODE != 'twelve_data':
        raise RuntimeError('Telegram delivery requires verified live data mode')
    # Provider's newest candle may still be forming; use index -2.
    closed_idx = len(candles) - 2
    if DATA_MODE == 'twelve_data':
        age = (datetime.now(timezone.utc) - _parse_time(candles[closed_idx].time)).total_seconds()
        if age < 0 or age > MAX_STALE_SECONDS:
            raise ValueError('Closed candle stale or future-dated; delivery refused')
    start = max(55, int(len(candles)*.70))
    events, trained = bot.alerts(candles, start, len(candles)-1,
                                  os.getenv('ML_ENABLED', 'true').lower() == 'true')
    latest = [e for e in events if e[1] == closed_idx]
    sent = 0
    if TELEGRAM_ENABLED:
        for event in latest:
            fingerprint = f'{TWELVE_SYMBOL}|{TWELVE_INTERVAL}|{event[0]}|{candles[closed_idx].time}|{event[2].side}|{event[3]}'
            with lock:
                if fingerprint in sent_events:
                    continue

                # Do not mark as delivered before Telegram confirms success.
                bot.notify(render(event, candles, TEMPLATE_STYLE), telegram=True)

                sent_events.add(fingerprint)
                try:
                    _persist_sent()
                except Exception:
                    sent_events.discard(fingerprint)
                    raise

                sent += 1

                # Best-effort history after confirmed delivery.
                # Failure here must not resend a delivered alert.
                try:
                    history = SignalHistory(HISTORY_DB)
                    try:
                        history.save_signal(
                            fingerprint,
                            TWELVE_SYMBOL,
                            TWELVE_INTERVAL,
                            event[0],
                            event[2].entry,
                            event[2].stop,
                            event[2].target,
                            candles[closed_idx].time
                        )
                    finally:
                        history.close()
                except Exception:
                    print('signal history write failed')

    with lock:
        state.update({'last_scan':datetime.now(timezone.utc).isoformat(), 'last_candle_time':candles[closed_idx].time,
                      'last_result':bot.report(events),'latest_events':[e[0] for e in latest],
                      'alerts_sent_last_scan':sent,'ml_trained':trained,'error':None})

def monitor():
    while True:
        try: scan_once()
        except Exception as exc:
            with lock: state['error'] = type(exc).__name__ + ': monitor failed; inspect server logs'
            print('monitor error:', type(exc).__name__)  # no provider/key exception content
        time.sleep(SCAN_SECONDS)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_GET(self):
        if self.path in ('/api/history', '/api/stats'):
            token = os.getenv('HISTORY_API_TOKEN', '')
            provided = self.headers.get('Authorization', '')

            if (not token or not hmac.compare_digest(
                provided, 'Bearer ' + token
            )):
                body, code = {'error': 'unauthorized'}, 401
            elif not HISTORY_DB.is_file():
                body, code = {'error': 'history unavailable'}, 503
            else:
                try:
                    history = SignalHistory(HISTORY_DB)
                    try:
                        if self.path == '/api/history':
                            body = {
                                'history': history.latest(20),
                                'mode': 'paper'
                            }
                        else:
                            body = history.stats()
                        code = 200
                    finally:
                        history.close()
                except Exception:
                    body, code = {'error': 'history unavailable'}, 503
        elif self.path == '/health':
            body, code = {'ok':True,'mode':'paper'},200
        elif self.path in ('/','/status'):
            with lock: body = dict(state)
            body.pop('error_detail',None)
            code=200
        else: body,code={'error':'not found'},404
        data=json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    threading.Thread(target=monitor,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','10000'))),Handler).serve_forever()
