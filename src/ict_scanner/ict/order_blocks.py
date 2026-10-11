from collections.abc import Sequence
from datetime import datetime
from math import isfinite

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle, OrderBlock


def find_order_block(
    candles: Sequence[Candle],
    direction: Direction,
    displacement_time: float | datetime,
) -> OrderBlock | None:
    """Find the last opposite-colored candle before the displacement leg."""
    if not candles or direction is Direction.NEUTRAL:
        return None

    if isinstance(displacement_time, datetime) and (
        displacement_time.tzinfo is None or displacement_time.utcoffset() is None
    ):
        raise ValueError("displacement_time must be timezone-aware")
    timestamp = (
        displacement_time.timestamp()
        if isinstance(displacement_time, datetime)
        else displacement_time
    )
    if not isfinite(timestamp):
        raise ValueError("displacement_time must be finite")

    for candle in reversed(candles):
        if candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None:
            raise ValueError("order-block candles must have timezone-aware timestamps")
        if candle.timestamp.timestamp() >= timestamp:
            continue

        if direction is Direction.BUY and candle.close < candle.open:
            return OrderBlock(
                direction=direction,
                low=candle.low,
                high=candle.high,
                candle=candle,
            )
        if direction is Direction.SELL and candle.close > candle.open:
            return OrderBlock(
                direction=direction,
                low=candle.low,
                high=candle.high,
                candle=candle,
            )

    return None
