import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import bot
import web_service as ws


class RestartRecoveryTests(unittest.TestCase):

    def test_persisted_alert_survives_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "alert-state.json"
            candles = bot.demo_data(100)
            timestamp = datetime.now(timezone.utc).isoformat()
            candles = [
                bot.Candle(timestamp, c.open, c.high, c.low, c.close, c.volume)
                for c in candles
            ]

            idx = len(candles) - 2
            signal = bot.Signal(
                "BUY", idx, 2500, 2495, 2510, 4,
                reason="restart test"
            )
            event = ("BUY", idx, signal, None, "entry", None)

            with (
                patch.object(ws, "STATE_FILE", path),
                patch.object(ws, "sent_events", set()) as sent,
                patch.object(ws, "DATA_MODE", "twelve_data"),
                patch.object(ws, "TELEGRAM_ENABLED", True),
                patch("web_service.bot.fetch_twelve_data",
                      return_value=candles),
                patch("web_service.bot.alerts",
                      return_value=([event], False)),
                patch("web_service.bot.report",
                      return_value={}),
                patch("web_service.bot.notify") as notify
            ):
                ws.scan_once()
                self.assertEqual(notify.call_count, 1)

                # Simulate state reloading after a restart.
                restored = ws._load_delivery()
                self.assertEqual(restored, sent)

                sent.clear()
                sent.update(restored)

                ws.scan_once()
                self.assertEqual(notify.call_count, 1)


if __name__ == "__main__":
    unittest.main()
