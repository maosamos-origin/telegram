import unittest
from signal_history import SignalHistory


class HistoryStatsTests(unittest.TestCase):
    def test_empty_stats(self):
        db = SignalHistory(":memory:")
        try:
            result = db.stats()
            self.assertEqual(result["total"], 0)
            self.assertEqual(result["buy"], 0)
            self.assertEqual(result["sell"], 0)
        finally:
            db.close()

    def test_counts(self):
        db = SignalHistory(":memory:")
        try:
            for i, side in enumerate(["BUY", "BUY", "SELL", "CLOSE"]):
                db.save_signal(
                    str(i), "XAU/USD", "5min", side,
                    2500, 2495, 2510, "2026-10-19T12:00:00Z"
                )

            result = db.stats()
            self.assertEqual(result["total"], 4)
            self.assertEqual(result["buy"], 2)
            self.assertEqual(result["sell"], 1)
            self.assertEqual(result["close"], 1)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
