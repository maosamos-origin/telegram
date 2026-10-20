
"""Unit tests for V2.4 paper-only exit decisions."""

import unittest

from exit_engine import evaluate_exit


def buy_position(peak=4250):
    return {
        "status": "OPEN",
        "side": "BUY",
        "entry": 4250.0,
        "stop": 4242.0,
        "target": 4266.0,
        "peak": peak,
    }


def sell_position(peak=4250):
    return {
        "status": "OPEN",
        "side": "SELL",
        "entry": 4250.0,
        "stop": 4258.0,
        "target": 4234.0,
        "peak": peak,
    }


class ExitEngineTests(unittest.TestCase):

    def test_buy_initial_hold(self):
        result = evaluate_exit(buy_position(), 4252)
        self.assertEqual(result["action"], "HOLD")

    def test_buy_pump_updates_peak(self):
        result = evaluate_exit(buy_position(), 4262)
        self.assertEqual(result["action"], "HOLD")
        self.assertEqual(result["peak"], 4262)
        self.assertEqual(result["protected_stop"], 4256)

    def test_buy_early_warning(self):
        result = evaluate_exit(
            buy_position(peak=4262), 4258
        )
        self.assertEqual(result["action"], "WARNING")
        self.assertEqual(result["protected_stop"], 4256)

    def test_buy_confirmed_close(self):
        result = evaluate_exit(
            buy_position(peak=4262), 4255
        )
        self.assertEqual(result["action"], "CLOSE")
        self.assertIn("trailing", result["reason"].lower())

    def test_buy_original_stop(self):
        result = evaluate_exit(buy_position(), 4242)
        self.assertEqual(result["action"], "CLOSE")
        self.assertIn("stop loss", result["reason"].lower())

    def test_buy_take_profit(self):
        result = evaluate_exit(buy_position(), 4266)
        self.assertEqual(result["action"], "CLOSE")
        self.assertIn("take profit", result["reason"].lower())

    def test_sell_initial_hold(self):
        result = evaluate_exit(sell_position(), 4248)
        self.assertEqual(result["action"], "HOLD")

    def test_sell_favorable_move(self):
        result = evaluate_exit(sell_position(), 4238)
        self.assertEqual(result["action"], "HOLD")
        self.assertEqual(result["peak"], 4238)
        self.assertEqual(result["protected_stop"], 4244)

    def test_sell_early_warning(self):
        result = evaluate_exit(
            sell_position(peak=4238), 4242
        )
        self.assertEqual(result["action"], "WARNING")

    def test_sell_confirmed_close(self):
        result = evaluate_exit(
            sell_position(peak=4238), 4245
        )
        self.assertEqual(result["action"], "CLOSE")
        self.assertIn("trailing", result["reason"].lower())

    def test_sell_original_stop(self):
        result = evaluate_exit(sell_position(), 4258)
        self.assertEqual(result["action"], "CLOSE")

    def test_sell_take_profit(self):
        result = evaluate_exit(sell_position(), 4234)
        self.assertEqual(result["action"], "CLOSE")

    def test_reject_closed_position(self):
        position = buy_position()
        position["status"] = "CLOSED"

        with self.assertRaises(ValueError):
            evaluate_exit(position, 4255)

    def test_reject_invalid_price(self):
        with self.assertRaises(ValueError):
            evaluate_exit(
                buy_position(), float("nan")
            )

    def test_reject_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            evaluate_exit(
                buy_position(),
                4255,
                warning_pullback_r=0.9,
                trailing_distance_r=0.75,
            )

    def test_buy_replay_warning_then_close(self):
        position = buy_position()
        actions = []

        for price in (4252, 4262, 4260, 4258, 4255):
            result = evaluate_exit(position, price)
            actions.append(result["action"])
            position["peak"] = result["peak"]

            if result["action"] == "CLOSE":
                position["status"] = "CLOSED"
                break

        self.assertEqual(
            actions,
            ["HOLD", "HOLD", "HOLD", "WARNING", "CLOSE"],
        )


if __name__ == "__main__":
    unittest.main()
