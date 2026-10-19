import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import bot
import web_service as ws
from signal_history import SignalHistory


class HistoryIntegrationTests(unittest.TestCase):

    def test_delivery_creates_one_history_record(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder) / "history.db"
            state_path = Path(folder) / "state.json"

            now = datetime.now(timezone.utc).isoformat()
            candles = [
                bot.Candle(now, 2500, 2502, 2498, 2500)
                for _ in range(100)
            ]

            idx = len(candles) - 2
            signal = bot.Signal(
                "BUY", idx, 2500, 2495, 2510, 4,
                reason="integration test"
            )
            event = ("BUY", idx, signal, None, "entry", None)

            with (
                patch.object(ws, "DATA_MODE", "twelve_data"),
                patch.object(ws, "TELEGRAM_ENABLED", True),
                patch.object(ws, "HISTORY_DB", db_path),
                patch.object(ws, "STATE_FILE", state_path),
                patch.object(ws, "sent_events", set()),
                patch("web_service.bot.fetch_twelve_data",
                      return_value=candles),
                patch("web_service.bot.alerts",
                      return_value=([event], False)),
                patch("web_service.bot.report",
                      return_value={}),
                patch("web_service.bot.notify") as notify
            ):
                ws.scan_once()
                ws.scan_once()

                self.assertEqual(notify.call_count, 1)

            history = SignalHistory(db_path)

            try:
                self.assertEqual(history.count(), 1)
                record = history.latest(1)[0]
                self.assertEqual(record["side"], "BUY")
                self.assertEqual(record["symbol"], "XAU/USD")
            finally:
                history.close()


if __name__ == "__main__":
    unittest.main()
