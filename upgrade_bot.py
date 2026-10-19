"""Run once from project root to guard historical/demo Telegram sends in bot.py.
This script intentionally fails closed if upstream code differs.
"""
from pathlib import Path
p = Path('bot.py')
s = p.read_text(encoding='utf-8')
old = '''    if a.command=="simulate":
        for e in events: notify(format_event(e,c), a.telegram and not a.dry_run)
        if not events: notify(f"XAUUSD WAIT | no qualifying setup in {c[start].time} to {c[-1].time}",a.telegram and not a.dry_run)'''
new = '''    if a.command=="simulate":
        if a.telegram and not a.dry_run:
            p.error("CLI historical simulation cannot send Telegram messages; use web_service.py with fresh validated live candles")
        for e in events: notify(format_event(e,c), False)
        if not events: notify(f"XAUUSD WAIT | no qualifying setup in {c[start].time} to {c[-1].time}",False)'''
if s.count(old) != 1:
    raise SystemExit('STOP: unsupported bot.py version; no changes made')
p.with_suffix('.py.v1-backup').write_text(s,encoding='utf-8')
p.write_text(s.replace(old,new,1),encoding='utf-8')
print('Patched bot.py; original saved to bot.py.v1-backup')
