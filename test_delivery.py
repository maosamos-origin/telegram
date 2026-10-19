import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import bot
import web_service as ws


class DeliveryTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        candles = bot.demo_data(100)
        now = datetime.now(timezone.utc).isoformat()

        self.candles = [
            bot.Candle(
                now,
                c.open,
                c.high,
                c.low,
                c.close,
                c.volume
            )
            for c in candles
        ]

        idx = len(self.candles) - 2

        signal = bot.Signal(
            "BUY",
            idx,
            2500.0,
            2495.0,
            2510.0,
            4.0,
            reason="unit test"
        )

        self.event = (
            "BUY",
            idx,
            signal,
            None,
            "entry",
            None
        )

        settings = {
            "DATA_MODE": "twelve_data",
            "TELEGRAM_ENABLED": True,
            "TEMPLATE_STYLE": "compact",
            "STATE_FILE": Path(self.tmp.name) / "state.json",
            "sent_events": set(),
        }

        for name, value in settings.items():
            p = patch.object(ws, name, value)
            p.start()
            self.addCleanup(p.stop)

        for target, value in [
            ("web_service.bot.fetch_twelve_data", self.candles),
            ("web_service.bot.alerts", ([self.event], False)),
            ("web_service.bot.report", {}),
        ]:
            p = patch(target, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def test_failed_send_does_not_mark_delivered(self):
        with patch(
            "web_service.bot.notify",
            side_effect=RuntimeError("simulated failure")
        ):
            with self.assertRaises(RuntimeError):
                ws.scan_once()

        self.assertEqual(len(ws.sent_events), 0)
        self.assertFalse(ws.STATE_FILE.exists())

    def test_successful_send_is_not_repeated(self):
        with patch("web_service.bot.notify") as notify:
            ws.scan_once()
            ws.scan_once()

        self.assertEqual(notify.call_count, 1)
        self.assertEqual(len(ws.sent_events), 1)
        self.assertTrue(ws.STATE_FILE.exists())


if __name__ == "__main__":
    unittest.main()
