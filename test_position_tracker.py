
"""Tests for V2.4 persistent paper positions."""

import tempfile
import unittest
from pathlib import Path

from position_tracker import PositionTracker


class PositionTrackerTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(
            Path(self.temp.name) / "positions.sqlite3"
        )
        self.tracker = PositionTracker(self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_open_buy(self):
        created = self.tracker.open_position(
            "buy-1", "BUY", 4250, 4242, 4266
        )
        self.assertTrue(created)

        position = self.tracker.get("buy-1")
        self.assertEqual(position["status"], "OPEN")
        self.assertEqual(position["peak"], 4250)

    def test_duplicate_id_is_rejected(self):
        self.assertTrue(self.tracker.open_position(
            "buy-1", "BUY", 4250, 4242, 4266
        ))
        self.assertFalse(self.tracker.open_position(
            "buy-1", "BUY", 4251, 4243, 4267
        ))
        self.assertEqual(
            self.tracker.get("buy-1")["entry"], 4250
        )

    def test_buy_peak_only_increases(self):
        self.tracker.open_position(
            "buy-1", "BUY", 4250, 4242, 4266
        )
        self.tracker.update_peak("buy-1", 4260)
        self.tracker.update_peak("buy-1", 4254)

        self.assertEqual(
            self.tracker.get("buy-1")["peak"], 4260
        )

    def test_sell_peak_tracks_lowest_price(self):
        self.tracker.open_position(
            "sell-1", "SELL", 4250, 4258, 4234
        )
        self.tracker.update_peak("sell-1", 4240)
        self.tracker.update_peak("sell-1", 4246)

        self.assertEqual(
            self.tracker.get("sell-1")["peak"], 4240
        )

    def test_position_survives_restart(self):
        self.tracker.open_position(
            "buy-1", "BUY", 4250, 4242, 4266
        )
        self.tracker.update_peak("buy-1", 4260)

        restarted = PositionTracker(self.db_path)

        self.assertEqual(
            restarted.get("buy-1")["peak"], 4260
        )
        self.assertEqual(
            len(restarted.get_open_positions()), 1
        )

    def test_close_only_once(self):
        self.tracker.open_position(
            "buy-1", "BUY", 4250, 4242, 4266
        )

        self.assertTrue(self.tracker.close_position(
            "buy-1", 4256, "confirmed reversal"
        ))
        self.assertFalse(self.tracker.close_position(
            "buy-1", 4254, "duplicate close"
        ))

        position = self.tracker.get("buy-1")
        self.assertEqual(position["status"], "CLOSED")
        self.assertEqual(position["close_price"], 4256)
        self.assertEqual(
            position["close_reason"], "confirmed reversal"
        )
        self.assertEqual(
            self.tracker.get_open_positions(), []
        )

    def test_closed_peak_cannot_change(self):
        self.tracker.open_position(
            "buy-1", "BUY", 4250, 4242, 4266
        )
        self.tracker.close_position(
            "buy-1", 4255, "confirmed reversal"
        )
        self.assertFalse(
            self.tracker.update_peak("buy-1", 4262)
        )

    def test_invalid_buy_levels(self):
        with self.assertRaises(ValueError):
            self.tracker.open_position(
                "bad-1", "BUY", 4250, 4260, 4270
            )

    def test_invalid_sell_levels(self):
        with self.assertRaises(ValueError):
            self.tracker.open_position(
                "bad-2", "SELL", 4250, 4240, 4230
            )

    def test_nan_prices_rejected(self):
        with self.assertRaises(ValueError):
            self.tracker.open_position(
                "bad-3", "BUY",
                float("nan"), 4242, 4266
            )

    def test_missing_position(self):
        self.assertIsNone(self.tracker.get("missing"))
        self.assertFalse(self.tracker.close_position(
            "missing", 4250, "not found"
        ))


if __name__ == "__main__":
    unittest.main()
