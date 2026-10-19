# XAUUSD Telegram V2 upgrade pack (paper only)

Copy `alert_templates.py`, `web_service.py`, `upgrade_bot.py`, and `test_templates.py` into your repository root. Check a clean Git working tree first, then run:

```bash
python3 upgrade_bot.py
python3 -m unittest -v test_templates.py test_bot.py
TELEGRAM_ENABLED=false PAPER_DATA_MODE=demo python3 web_service.py
```

Then GET `/status`; no Telegram messages should be sent. For delivery to group, use a live provider and `PAPER_DATA_MODE=twelve_data`, `TELEGRAM_ENABLED=true`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TWELVE_DATA_API_KEYS`. Only set `MARKET_DATA_TIMEZONE=UTC` after verifying provider candle times are UTC. `TELEGRAM_TEMPLATE` = premium, compact, technical, or minimal. Always use a **persistent** `ALERT_STATE_FILE` on production for deduplication. Free ephemeral Render storage will not persist across redeploys. This upgrade assumes a **single service instance**. The alert marker uses at-most-once semantics: Telegram transient failures can result in missed alerts rather than duplicates. For production delivery guarantees, replace marker approach with a persistent queue/outbox and reconciliation. Health endpoint indicates HTTP liveness, not market-data readiness. Backtest lacks spread/slippage, so do not treat reported win rate as real-world performance.

The original `render.yaml` intentionally defaults to demo and has Telegram disabled. Do not change until tested.
