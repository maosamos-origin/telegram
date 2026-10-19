import tempfile
import threading
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
        history.close()

        self.day = "2026-10-19"

    def test_successful_delivery(self):
        sender = DailySender(self.path)
        notify = Mock()
        try:
            self.assertTrue(sender.send(self.day, notify))
            self.assertEqual(sender.status(self.day), "sent")
            notify.assert_called_once()
        finally:
            sender.close()

    def test_duplicate_prevention(self):
        sender = DailySender(self.path)
        notify = Mock()
        try:
            self.assertTrue(sender.send(self.day, notify))
            self.assertFalse(sender.send(self.day, notify))
            notify.assert_called_once()
        finally:
            sender.close()

    def test_failure_requires_manual_reconciliation(self):
        sender = DailySender(self.path)
        notify = Mock(side_effect=RuntimeError("network failed"))
        try:
            with self.assertRaises(RuntimeError):
                sender.send(self.day, notify)

            self.assertEqual(sender.status(self.day), "pending")

            # No automatic retry: delivery outcome is ambiguous.
            self.assertFalse(sender.send(self.day, notify))
            self.assertEqual(notify.call_count, 1)
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
            self.assertEqual(second.status(self.day), "sent")
            self.assertFalse(second.send(self.day, notify))
            notify.assert_not_called()
        finally:
            second.close()

    def test_invalid_day_rejected(self):
        sender = DailySender(self.path)
        try:
            with self.assertRaises(ValueError):
                sender.send("invalid-date", Mock())
        finally:
            sender.close()

    def test_two_workers_only_one_sends(self):
        started = threading.Event()
        release = threading.Event()
        results = []
        errors = []

        def notify(_message):
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Test synchronization timed out")

        def worker():
            sender = None
            try:
                sender = DailySender(self.path)
                results.append(sender.send(self.day, notify))
            except Exception as exc:
                errors.append(exc)
            finally:
                if sender is not None:
                    sender.close()

        first = threading.Thread(target=worker)
        second = threading.Thread(target=worker)

        first.start()
        try:
            self.assertTrue(started.wait(timeout=5))
            second.start()
        finally:
            release.set()
            first.join(timeout=5)
            if second.ident is not None:
                second.join(timeout=5)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(sorted(results), [False, True])


if __name__ == "__main__":
    unittest.main()
