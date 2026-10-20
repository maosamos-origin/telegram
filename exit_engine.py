
"""V2.4 paper-only profit protection engine.

Pure decision logic. No network, Telegram, database
writes, or broker orders.

Thresholds are experimental and require backtesting.
"""

import math


def evaluate_exit(
    position,
    price,
    activation_r=1.0,
    warning_pullback_r=0.4,
    trailing_distance_r=0.75,
):
    """Evaluate a paper position using one observed price.

    Returns action: HOLD, WARNING, or CLOSE.

    Caller must separately handle data freshness,
    position persistence, alert deduplication, and
    notification delivery.
    """
    if position["status"] != "OPEN":
        raise ValueError("Position is not open")

    side = position["side"]
    if side not in ("BUY", "SELL"):
        raise ValueError("Invalid position side")

    def valid_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
        )

    fields = (
        position["entry"],
        position["stop"],
        position["target"],
        position["peak"],
        price,
    )

    if not all(valid_number(x) for x in fields):
        raise ValueError("Invalid or non-finite price")

    parameters = (
        activation_r,
        warning_pullback_r,
        trailing_distance_r,
    )

    if not all(valid_number(x) for x in parameters):
        raise ValueError("Invalid protection parameters")

    if warning_pullback_r >= trailing_distance_r:
        raise ValueError(
            "Warning must precede the trailing exit"
        )

    entry = position["entry"]
    stop = position["stop"]
    target = position["target"]
    old_peak = position["peak"]

    if side == "BUY":
        if not (stop < entry < target):
            raise ValueError("Invalid BUY levels")
        peak = max(old_peak, price)
        risk = entry - stop
        favorable = peak - entry
        retracement = peak - price
        hit_sl = price <= stop
        hit_tp = price >= target
    else:
        if not (target < entry < stop):
            raise ValueError("Invalid SELL levels")
        peak = min(old_peak, price)
        risk = stop - entry
        favorable = entry - peak
        retracement = price - peak
        hit_sl = price >= stop
        hit_tp = price <= target

    result = {
        "action": "HOLD",
        "reason": "Position remains open",
        "price": price,
        "peak": peak,
        "risk": risk,
        "protected_stop": stop,
    }

    if hit_sl:
        result.update(
            action="CLOSE",
            reason="Original stop loss reached",
        )
        return result

    if hit_tp:
        result.update(
            action="CLOSE",
            reason="Take profit reached",
        )
        return result

    # Protection activates only after favorable
    # movement reaches the configured R multiple.
    if favorable < activation_r * risk:
        return result

    # Lock in break-even or a more favorable
    # trailing level after sufficient movement.
    if side == "BUY":
        protected_stop = max(
            entry,
            peak - trailing_distance_r * risk,
        )
        hit_protection = price <= protected_stop
    else:
        protected_stop = min(
            entry,
            peak + trailing_distance_r * risk,
        )
        hit_protection = price >= protected_stop

    result["protected_stop"] = protected_stop

    if hit_protection:
        result.update(
            action="CLOSE",
            reason="Protected trailing exit confirmed",
        )
        return result

    if retracement >= warning_pullback_r * risk:
        result.update(
            action="WARNING",
            reason="Profit pullback detected",
        )

    return result
