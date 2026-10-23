"""Safe, dependency-free Telegram text templates for paper XAUUSD signals."""
import math
import re
from datetime import datetime, timedelta, timezone

STYLES = ('premium', 'compact', 'technical', 'minimal', 'khmer', 'khmer_compact')

def _num(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite signal price')
    return f'{value:,.2f}'

_PHNOM_PENH = timezone(timedelta(hours=7))  # Cambodia has no daylight saving
_LINE = '━━━━━━━━━━━━━━━━━━'
_CLOSE_KH = {
    'take profit': '✅ ទទួលបានចំណេញ (Take Profit)',
    'stop loss': '🛑 ប៉ះកម្រិតទប់ការខាត (Stop Loss)',
    'trend reversal': '🔄 ទិសដៅទីផ្សារប្តូរ (Trend Reversal)',
}

def _time_kh(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_PHNOM_PENH).strftime('%d/%m/%Y %H:%M')

def _reason_kh(text):
    text = str(text)
    if text.startswith('EMA trend + liquidity sweep'):
        base = 'ទិសដៅ EMA + liquidity sweep'
    elif text.startswith('EMA trend pullback'):
        base = 'ទិសដៅ EMA + pullback ទៅ EMA20 + candle បដិសេធ'
    else:
        return text
    parts = [base]
    for name in ('RSI', 'ATR'):
        m = re.search(name + r' (\d+(?:\.\d+)?)', text)
        if m:
            parts.append(f'{name} {m.group(1)}')
    return ' • '.join(parts)

def _render_khmer(event, candles, style):
    kind, index, signal, price, reason, pnl = event
    when = _time_kh(candles[index].time)
    compact = style == 'khmer_compact'
    if kind == 'CLOSE':
        sign = '+' if pnl > 0 else ''
        result = '✅ ចំណេញ' if pnl > 0 else ('❌ ខាត' if pnl < 0 else '➖ ស្មើ')
        why = _CLOSE_KH.get(str(reason), str(reason))
        side_emoji = '🟢' if signal.side == 'BUY' else '🔴'
        if compact:
            return (f'🔔 XAUUSD បិទ (CLOSE) {signal.side} {side_emoji}\n'
                    f'ចេញ {_num(price)} | {sign}{pnl:.2f} {result}\n'
                    f'📌 {why}\n⚠️ សញ្ញាសាកល្បង')
        return (f'🔔 XAUUSD • បិទការជួញដូរ (CLOSE)\n{_LINE}\n'
                f'{side_emoji} ទិសដៅ: {signal.side}\n'
                f'💵 តម្លៃចេញ: {_num(price)}\n'
                f'📈 ចលនាតម្លៃ: {sign}{pnl:.2f} {result}\n'
                f'   (ក្នុងមួយអោន មិនមែនចំណេញគណនីទេ)\n'
                f'📌 មូលហេតុ: {why}\n'
                f'🕒 ម៉ោងភ្នំពេញ: {when}\n\n'
                f'⚠️ សញ្ញាសាកល្បង (Paper) • មិនមែនជាដំបូន្មានវិនិយោគ')
    if kind not in ('BUY', 'SELL'):
        raise ValueError('Unexpected event type')
    emoji = '🟢' if kind == 'BUY' else '🔴'
    word = 'ទិញ' if kind == 'BUY' else 'លក់'
    risk = abs(signal.entry - signal.stop)
    rr = abs(signal.target - signal.entry) / risk if risk else 0
    if compact:
        return (f'{emoji} XAUUSD {word} ({kind})\n'
                f'ចូល {_num(signal.entry)}\n'
                f'SL {_num(signal.stop)} | TP {_num(signal.target)}\n'
                f'R:R 1:{rr:.2f}\n⚠️ សញ្ញាសាកល្បង')
    return (f'🥇 XAUUSD • សញ្ញាមាស\n{_LINE}\n'
            f'{emoji} {word} ({kind})\n\n'
            f'💰 តម្លៃចូល: {_num(signal.entry)}\n'
            f'🛑 ទប់ការខាត (SL): {_num(signal.stop)}\n'
            f'🎯 យកចំណេញ (TP): {_num(signal.target)}\n'
            f'⚖️ ហានិភ័យ : ចំណេញ = 1 : {rr:.2f}\n\n'
            f'🧠 ហេតុផល: {_reason_kh(signal.reason)}\n'
            f'📊 ពិន្ទុម៉ូដែល: {signal.score:.2f} (មិនមែនប្រូបាប៊ីលីតេឈ្នះ)\n'
            f'🕒 ម៉ោងភ្នំពេញ: {when}\n\n'
            f'⚠️ សញ្ញាសាកល្បង (Paper) • មិនមែនជាដំបូន្មានវិនិយោគ')

def render(event, candles, style='premium'):
    if style not in STYLES:
        raise ValueError(f'Unknown template {style!r}')
    if style.startswith('khmer'):
        return _render_khmer(event, candles, style)
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
