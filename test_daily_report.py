import tempfile
import unittest
from pathlib import Path

from daily_report import daily_stats, render_daily_report
from signal_history import SignalHistory


class DailyReportTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "history.db"

    def test_missing_database(self):
        with self.assertRaises(FileNotFoundError):
            daily_stats(self.path, "2026-10-19")

    def test_empty_day(self):
        db = SignalHistory(self.path)
        db.close()

        result = daily_stats(self.path, "2026-10-19")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["buy"], 0)

    def test_daily_counts_and_date_isolation(self):
        db = SignalHistory(self.path)
        try:
            for i, side in enumerate(["BUY", "BUY", "SELL", "CLOSE"]):
                db.save_signal(
                    f"signal-{i}", "XAU/USD", "5min",
                    side, 2500, 2495, 2510,
                    "2026-10-19T10:00:00Z"
                )

            # Assign explicit dates for a deterministic test.
            db.db.execute(
                """
                UPDATE signals
                SET created_at = '2026-10-19T12:00:00+00:00'
                WHERE fingerprint IN (
                    'signal-0', 'signal-1', 'signal-2'
                )
                """
            )
            db.db.execute(
                """
                UPDATE signals
                SET created_at = '2026-10-18T12:00:00+00:00'
                WHERE fingerprint = 'signal-3'
                """
            )
            db.db.commit()
        finally:
            db.close()

        today = daily_stats(self.path, "2026-10-19")
        yesterday = daily_stats(self.path, "2026-10-18")

        self.assertEqual(today["total"], 3)
        self.assertEqual(today["buy"], 2)
        self.assertEqual(today["sell"], 1)
        self.assertEqual(today["close"], 0)

        self.assertEqual(yesterday["total"], 1)
        self.assertEqual(yesterday["close"], 1)

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            daily_stats(self.path, "2026-99-99")

    def test_report_template(self):
        stats = {
            "date": "2026-10-19",
            "buy": 2,
            "sell": 1,
            "close": 1,
            "total": 4,
        }

        message = render_daily_report(stats)

        self.assertIn("BUY: 2", message)
        self.assertIn("SELL: 1", message)
        self.assertIn("CLOSE: 1", message)
        self.assertIn("TOTAL: 4", message)
        self.assertIn("PAPER", message)
        self.assertIn("Not win rate", message)


if __name__ == "__main__":
    unittest.main()
