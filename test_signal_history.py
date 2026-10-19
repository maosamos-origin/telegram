import tempfile
import unittest
from pathlib import Path

from signal_history import SignalHistory


class SignalHistoryTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "signals.db"

    def test_save_and_find(self):
        history = SignalHistory(self.path)

        saved = history.save_signal(
            "signal-001",
            "XAU/USD",
            "5min",
            "BUY",
            2500,
            2495,
            2510,
            "2026-10-19T10:00:00Z"
        )

        self.assertTrue(saved)
        self.assertTrue(history.exists("signal-001"))
        self.assertEqual(history.count(), 1)

        history.close()

    def test_prevent_duplicate(self):
        history = SignalHistory(self.path)

        args = (
            "signal-002", "XAU/USD", "5min",
            "SELL", 2500, 2505, 2490,
            "2026-10-19T10:05:00Z"
        )

        self.assertTrue(history.save_signal(*args))
        self.assertFalse(history.save_signal(*args))
        self.assertEqual(history.count(), 1)

        history.close()

    def test_restart_persistence(self):
        first = SignalHistory(self.path)

        first.save_signal(
            "signal-003",
            "XAU/USD",
            "5min",
            "BUY",
            2500,
            2495,
            2510,
            "2026-10-19T10:10:00Z"
        )

        first.close()

        second = SignalHistory(self.path)

        self.assertTrue(second.exists("signal-003"))
        self.assertEqual(second.count(), 1)

        second.close()

    def test_latest_history(self):
        history = SignalHistory(self.path)

        history.save_signal(
            "signal-004",
            "XAU/USD",
            "5min",
            "BUY",
            2500,
            2495,
            2510,
            "2026-10-19T10:15:00Z"
        )

        rows = history.latest()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["side"], "BUY")

        history.close()


if __name__ == "__main__":
    unittest.main()
