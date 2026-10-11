from math import isfinite

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import FVG, OrderBlock


def calculate_levels(
    direction: Direction,
    sweep_extreme: float,
    fvg: FVG,
    ob: OrderBlock | None,
    atr_buffer: float,
    fib_levels: dict[float, float],
) -> tuple[float, float, float, float]:
    """Calculate Entry, Stop Loss, TP1, and TP2."""
    if direction is Direction.NEUTRAL:
        raise ValueError("a directional trade plan requires BUY or SELL")
    if (
        not all(isfinite(value) for value in (sweep_extreme, atr_buffer, fvg.low, fvg.high))
        or atr_buffer < 0
        or fvg.low >= fvg.high
    ):
        raise ValueError("trade-plan prices and buffer must be finite and the FVG non-empty")
    if 0.618 not in fib_levels or 0.786 not in fib_levels or -0.27 not in fib_levels:
        raise ValueError("fib_levels must include 0.618, 0.786, and -0.27")

    ote_low = min(fib_levels[0.618], fib_levels[0.786])
    ote_high = max(fib_levels[0.618], fib_levels[0.786])
    fvg_midpoint = (fvg.low + fvg.high) / 2.0
    entry = fvg_midpoint
    if ob is not None:
        overlap_low = max(fvg.low, ob.low, ote_low)
        overlap_high = min(fvg.high, ob.high, ote_high)
        if overlap_low <= overlap_high:
            entry = (overlap_low + overlap_high) / 2.0
        elif ote_low <= ob.candle.open <= ote_high:
            entry = ob.candle.open

    if direction == Direction.BUY:
        sl = sweep_extreme - atr_buffer
        risk = entry - sl
        if risk <= 0:
            raise ValueError("BUY stop loss must be below entry")
        tp1 = entry + 2.0 * risk
        tp2 = max(fib_levels[-0.27], entry + 3.0 * risk)
    else:
        sl = sweep_extreme + atr_buffer
        risk = sl - entry
        if risk <= 0:
            raise ValueError("SELL stop loss must be above entry")
        tp1 = entry - 2.0 * risk
        tp2 = min(fib_levels[-0.27], entry - 3.0 * risk)

    return entry, sl, tp1, tp2


def calculate_rr(entry: float, sl: float, tp: float) -> float:
    risk = abs(entry - sl)
    if not all(isfinite(value) for value in (entry, sl, tp)) or risk == 0:
        return 0.0
    reward = abs(tp - entry)
    return reward / risk
