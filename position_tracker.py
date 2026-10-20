
"""Persistent paper-position tracking for XAUUSD V2.4.

Not connected to live monitoring or broker execution.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class PositionTracker:
    def __init__(self, db_path="positions.sqlite3"):
        self.db_path = db_path
        self.initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=10000")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    position_id TEXT PRIMARY KEY,
                    side TEXT NOT NULL,
                    entry REAL NOT NULL,
                    stop REAL NOT NULL,
                    target REAL NOT NULL,
                    peak REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    close_price REAL,
                    close_reason TEXT,
                    CHECK (side IN ('BUY', 'SELL')),
                    CHECK (status IN ('OPEN', 'CLOSED'))
                )
            """)

    def get(self, position_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM positions WHERE position_id = ?",
                (position_id,),
            ).fetchone()

        return dict(row) if row else None

    def open_position(
        self, position_id, side, entry, stop, target
    ):
        if not position_id or not isinstance(position_id, str):
            raise ValueError("Position ID is required")

        if side not in ("BUY", "SELL"):
            raise ValueError("Invalid position side")

        import math
        values = (entry, stop, target)
        if not all(
            isinstance(x, (int, float))
            and not isinstance(x, bool)
            and math.isfinite(x)
            and x > 0
            for x in values
        ):
            raise ValueError("Invalid position prices")

        if side == "BUY" and not (stop < entry < target):
            raise ValueError("Invalid BUY risk levels")

        if side == "SELL" and not (target < entry < stop):
            raise ValueError("Invalid SELL risk levels")

        with self.connect() as db:
            cursor = db.execute("""
                INSERT OR IGNORE INTO positions (
                    position_id, side, entry, stop,
                    target, peak, opened_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                position_id, side, entry, stop,
                target, entry, utc_now(),
            ))

            return cursor.rowcount == 1

    def update_peak(self, position_id, price):
        import math
        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid market price")

        with self.connect() as db:
            cursor = db.execute("""
                UPDATE positions
                SET peak = CASE
                    WHEN side = 'BUY' AND ? > peak THEN ?
                    WHEN side = 'SELL' AND ? < peak THEN ?
                    ELSE peak
                END
                WHERE position_id = ?
                  AND status = 'OPEN'
            """, (
                price, price, price, price, position_id
            ))

            return cursor.rowcount == 1

    def close_position(
        self, position_id, price, reason
    ):
        import math
        if not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid close price")

        if not reason:
            raise ValueError("Close reason is required")

        with self.connect() as db:
            cursor = db.execute("""
                UPDATE positions
                SET status = 'CLOSED',
                    closed_at = ?,
                    close_price = ?,
                    close_reason = ?
                WHERE position_id = ?
                  AND status = 'OPEN'
            """, (
                utc_now(), price, reason, position_id
            ))

            return cursor.rowcount == 1

    def get_open_positions(self):
        with self.connect() as db:
            rows = db.execute("""
                SELECT * FROM positions
                WHERE status = 'OPEN'
                ORDER BY opened_at
            """).fetchall()

        return [dict(row) for row in rows]
