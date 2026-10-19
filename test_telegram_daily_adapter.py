import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signal_history import SignalHistory
from telegram_daily_adapter import send_daily_report


class TelegramDailyAdapterTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.path = Path(self.tmp.name) / "history.db"
        history = SignalHistory(self.path)
        history.close()

        self.day = "2026-10-19"

    @patch("telegram_daily_adapter.bot.notify")
    def test_disabled_by_default(self, notify):
        with patch.dict(os.environ, {}, clear=True):
            result = send_daily_report(
                self.path, self.day, allow_network=True
            )

        self.assertEqual(result, "disabled")
        notify.assert_not_called()

    @patch("telegram_daily_adapter.bot.notify")
    def test_explicit_network_consent_required(self, notify):
        with patch.dict(
            os.environ,
            {"DAILY_REPORT_TELEGRAM_ENABLED": "true"}
        ):
            result = send_daily_report(self.path, self.day)

        self.assertEqual(result, "disabled")
        notify.assert_not_called()

    @patch("telegram_daily_adapter.bot.notify")
    def test_mock_delivery_and_deduplication(self, notify):
        with patch.dict(
            os.environ,
            {"DAILY_REPORT_TELEGRAM_ENABLED": "true"}
        ):
            first = send_daily_report(
                self.path, self.day, allow_network=True
            )
            second = send_daily_report(
                self.path, self.day, allow_network=True
            )

        self.assertEqual(first, "sent")
        self.assertEqual(second, "sent")
        notify.assert_called_once()

    @patch("telegram_daily_adapter.bot.notify")
    def test_ambiguous_failure_remains_pending(self, notify):
        notify.side_effect = RuntimeError("network error")

        with patch.dict(
            os.environ,
            {"DAILY_REPORT_TELEGRAM_ENABLED": "true"}
        ):
            with self.assertRaises(RuntimeError):
                send_daily_report(
                    self.path, self.day, allow_network=True
                )

            result = send_daily_report(
                self.path, self.day, allow_network=True
            )

        self.assertEqual(result, "pending")
        notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
