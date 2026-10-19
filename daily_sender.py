"""Daily report delivery coordinator for paper signals.

No automatic execution and no direct Telegram network calls.
"""

import sqlite3
from pathlib import Path

from daily_report import daily_stats, render_daily_report


class DailySender:
    def __init__(self, database_path):
        self.path = Path(database_path)
        if not self.path.is_file():
            raise FileNotFoundError("History database unavailable")

        self.db = sqlite3.connect(str(self.path))
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS daily_deliveries (
                day TEXT PRIMARY KEY,
                delivered_at TEXT NOT NULL
            )
        """)
        self.db.commit()

    def already_sent(self, day):
        return self.db.execute(
            "SELECT 1 FROM daily_deliveries WHERE day = ?",
            (day,)
        ).fetchone() is not None

    def prepare(self, day):
        stats = daily_stats(self.path, day)
        return render_daily_report(stats)

    def send(self, day, send_function):
        # Validate day before deduplication.
        message = self.prepare(day)

        if self.already_sent(day):
            return False

        # The callback must raise on any unsuccessful or ambiguous
        # delivery. None is treated as success only for test callbacks.
        send_function(message)

        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

        with self.db:
            self.db.execute(
                """
                INSERT OR IGNORE INTO daily_deliveries
                (day, delivered_at) VALUES (?, ?)
                """,
                (day, timestamp)
            )

        return True

    def close(self):
        self.db.close()
