"""Daily paper-signal report. No Telegram network calls."""

from datetime import datetime, timezone
from pathlib import Path

from signal_history import SignalHistory


def daily_stats(database_path, day=None):
    """Count confirmed-history records by UTC calendar day."""
    if day is None:
        day = datetime.now(timezone.utc).date().isoformat()

    # Strict date validation avoids accepting malformed dates.
    parsed = datetime.strptime(day, "%Y-%m-%d").date()
    if parsed.isoformat() != day:
        raise ValueError("Invalid UTC date")

    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError("Signal history database unavailable")

    history = SignalHistory(path)
    try:
        rows = history.db.execute(
            """
            SELECT side, COUNT(*)
            FROM signals
            WHERE substr(created_at, 1, 10) = ?
            GROUP BY side
            """,
            (day,)
        ).fetchall()
    finally:
        history.close()

    counts = {"BUY": 0, "SELL": 0, "CLOSE": 0}
    for side, count in rows:
        if side in counts:
            counts[side] = count

    return {
        "date": day,
        "timezone": "UTC",
        "total": sum(counts.values()),
        "buy": counts["BUY"],
        "sell": counts["SELL"],
        "close": counts["CLOSE"],
        "mode": "paper",
    }


def render_daily_report(stats):
    """Format a human-readable Telegram message; do not send it."""
    return (
        "XAUUSD | DAILY SIGNAL REPORT\n"
        f"Date: {stats['date']} (UTC)\n"
        "Mode: PAPER\n"
        "-------------------------\n"
        f"BUY: {stats['buy']}\n"
        f"SELL: {stats['sell']}\n"
        f"CLOSE: {stats['close']}\n"
        f"TOTAL: {stats['total']}\n"
        "-------------------------\n"
        "Alert counts only. Not win rate or realized P/L."
    )
