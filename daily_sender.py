"""Crash-aware daily report delivery coordinator.

No automatic execution or direct Telegram network calls.
Pending deliveries require manual reconciliation.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from daily_report import daily_stats, render_daily_report


class DailySender:
    def __init__(self, database_path):
        self.path = Path(database_path)
        if not self.path.is_file():
            raise FileNotFoundError("History database unavailable")

        self.db = sqlite3.connect(str(self.path), timeout=5)
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS daily_delivery_claims (
                day TEXT PRIMARY KEY,
                status TEXT NOT NULL
                    CHECK(status IN ('pending', 'sent')),
                claimed_at TEXT NOT NULL,
                delivered_at TEXT
            )
        """)
        self.db.commit()

    def status(self, day):
        row = self.db.execute(
            "SELECT status FROM daily_delivery_claims WHERE day = ?",
            (day,)
        ).fetchone()
        return row[0] if row else None

    def already_sent(self, day):
        return self.status(day) == "sent"

    def prepare(self, day):
        stats = daily_stats(self.path, day)
        return render_daily_report(stats)

    def send(self, day, send_function):
        message = self.prepare(day)
        now = datetime.now(timezone.utc).isoformat()

        # Atomic claim across processes sharing this SQLite database.
        try:
            self.db.execute("BEGIN IMMEDIATE")
            cursor = self.db.execute(
                """
                INSERT OR IGNORE INTO daily_delivery_claims
                    (day, status, claimed_at)
                VALUES (?, 'pending', ?)
                """,
                (day, now)
            )
            claimed = cursor.rowcount == 1
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        if not claimed:
            return False

        # A failure or crash leaves 'pending' for manual review.
        # Never automatically retry an ambiguous Telegram delivery.
        send_function(message)

        completed_at = datetime.now(timezone.utc).isoformat()

        with self.db:
            self.db.execute(
                """
                UPDATE daily_delivery_claims
                SET status = 'sent', delivered_at = ?
                WHERE day = ? AND status = 'pending'
                """,
                (completed_at, day)
            )

        return True

    def close(self):
        self.db.close()
