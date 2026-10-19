"""Safe, dependency-free Telegram text templates for paper XAUUSD signals."""
import math

STYLES = ('premium', 'compact', 'technical', 'minimal')

def _num(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite signal price')
    return f'{value:,.2f}'

def render(event, candles, style='premium'):
    if style not in STYLES:
        raise ValueError(f'Unknown template {style!r}')
    kind, index, signal, price, reason, pnl = event
    when = candles[index].time
    if kind == 'CLOSE':
        sign = '+' if pnl > 0 else ''
        if style == 'minimal':
            return f'XAUUSD CLOSE {signal.side} | {_num(price)} | P/L {sign}{pnl:.2f}\nPaper only'
        return (f'🔔 XAUUSD • POSITION CLOSED\n\nSide: {signal.side}\nExit: {_num(price)}\n'
                f'Price movement: {sign}{pnl:.2f} (per oz, not account P/L)\n'
                f'Reason: {reason}\nCandle: {when}\n⚠️ Paper signal only')
    if kind not in ('BUY', 'SELL'):
        raise ValueError('Unexpected event type')
    emoji = '🟢' if kind == 'BUY' else '🔴'
    risk = abs(signal.entry - signal.stop)
    reward = abs(signal.target - signal.entry)
    rr = reward / risk if risk else 0
    score = f'{signal.score:.2f}'
    if style == 'minimal':
        return (f'XAUUSD {kind} {emoji}\nEntry {_num(signal.entry)}\n'
                f'SL {_num(signal.stop)} | TP {_num(signal.target)}\nPaper only')
    if style == 'compact':
        return (f'{emoji} XAUUSD {kind}\nEntry {_num(signal.entry)}\n'
                f'SL {_num(signal.stop)} | TP {_num(signal.target)}\n'
                f'R:R 1:{rr:.2f} | Model score {score}\n⚠️ Paper only')
    if style == 'technical':
        return (f'📊 XAUUSD • TECHNICAL SIGNAL\nDirection: {kind} {emoji}\n'
                f'Entry: {_num(signal.entry)}\nStop: {_num(signal.stop)}\n'
                f'Target: {_num(signal.target)}\nR:R: 1:{rr:.2f}\n'
                f'Model score: {score} (not calibrated win probability)\n'
                f'Analysis: {signal.reason}\nCandle: {when}\n⚠️ Paper only')
    return (f'🥇 XAUUSD • GOLD SIGNAL\n━━━━━━━━━━━━━━━━━━\n{emoji} {kind} OPPORTUNITY\n\n'
            f'💰 Entry: {_num(signal.entry)}\n🛑 Stop Loss: {_num(signal.stop)}\n'
            f'🎯 Take Profit: {_num(signal.target)}\n⚖️ Risk/Reward: 1:{rr:.2f}\n'
            f'📊 Model score: {score} (not win probability)\n🧠 {signal.reason}\n'
            f'🕒 Candle: {when}\n⚠️ Paper signal • Not financial advice')

def wait_message(candle_time):
    return f'⏳ XAUUSD WAIT\nNo validated entry at {candle_time}.\n⚠️ Paper mode'

def error_message():
    return '⚠️ XAUUSD signal monitor temporarily unavailable. No trade recommendation; check data feed.'
