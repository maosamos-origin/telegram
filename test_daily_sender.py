import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from daily_sender import DailySender
from signal_history import SignalHistory


class DailySenderTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "history.db"

        history = SignalHistory(self.path)
        history.save_signal(
            "signal-test", "XAU/USD", "5min",
            "BUY", 2500, 2495, 2510,
            "2026-10-19T10:00:00Z"
        )
        history.close()

        self.day = "2026-10-19"

    def test_successful_delivery(self):
        sender = DailySender(self.path)
        notify = Mock()

        try:
            self.assertTrue(sender.send(self.day, notify))
            self.assertEqual(notify.call_count, 1)
            self.assertTrue(sender.already_sent(self.day))
        finally:
            sender.close()

    def test_duplicate_prevention(self):
        sender = DailySender(self.path)
        notify = Mock()

        try:
            self.assertTrue(sender.send(self.day, notify))
            self.assertFalse(sender.send(self.day, notify))
            self.assertEqual(notify.call_count, 1)
        finally:
            sender.close()

    def test_failed_delivery_can_retry(self):
        sender = DailySender(self.path)
        notify = Mock(side_effect=RuntimeError("network failed"))

        try:
            with self.assertRaises(RuntimeError):
                sender.send(self.day, notify)

            self.assertFalse(sender.already_sent(self.day))

            notify.side_effect = None
            self.assertTrue(sender.send(self.day, notify))
        finally:
            sender.close()

    def test_restart_persistence(self):
        first = DailySender(self.path)

        try:
            self.assertTrue(first.send(self.day, Mock()))
        finally:
            first.close()

        second = DailySender(self.path)

        try:
            notify = Mock()
            self.assertFalse(second.send(self.day, notify))
            notify.assert_not_called()
        finally:
            second.close()

    def test_invalid_day_rejected(self):
        sender = DailySender(self.path)
        notify = Mock()

        try:
            with self.assertRaises(ValueError):
                sender.send("invalid-date", notify)
            notify.assert_not_called()
        finally:
            sender.close()


if __name__ == "__main__":
    unittest.main()
