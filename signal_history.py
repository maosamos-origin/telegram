"""SQLite signal history for paper trading only."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SignalHistory:
    def __init__(self, database_path="signal-history.db"):
        self.path = Path(database_path)

        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)

        self.db = sqlite3.connect(str(self.path))
        self.db.execute("PRAGMA busy_timeout=5000")

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                fingerprint TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                side TEXT NOT NULL,
                entry REAL,
                stop_loss REAL,
                take_profit REAL,
                candle_time TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.db.commit()

    def save_signal(
        self, fingerprint, symbol, timeframe, side,
        entry, stop_loss, take_profit, candle_time
    ):
        if side not in ("BUY", "SELL", "CLOSE"):
            raise ValueError("Invalid signal side")

        timestamp = datetime.now(timezone.utc).isoformat()

        with self.db:
            cursor = self.db.execute(
                """
                INSERT OR IGNORE INTO signals (
                    fingerprint, symbol, timeframe, side,
                    entry, stop_loss, take_profit,
                    candle_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint, symbol, timeframe, side,
                    entry, stop_loss, take_profit,
                    candle_time, timestamp
                )
            )

        return cursor.rowcount == 1

    def exists(self, fingerprint):
        row = self.db.execute(
            "SELECT 1 FROM signals WHERE fingerprint = ?",
            (fingerprint,)
        ).fetchone()

        return row is not None

    def latest(self, limit=20):
        limit = max(1, min(int(limit), 100))

        self.db.row_factory = sqlite3.Row

        rows = self.db.execute(
            """
            SELECT * FROM signals
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [dict(row) for row in rows]

    def count(self):
        return self.db.execute(
            "SELECT COUNT(*) FROM signals"
        ).fetchone()[0]

    def close(self):
        self.db.close()
