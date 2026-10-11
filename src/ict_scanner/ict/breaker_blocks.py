from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle, OrderBlock


@dataclass(frozen=True)
class BreakerBlock:
    direction: Direction
    low: float
    high: float
    source_order_block: OrderBlock
    break_time: datetime


def detect_breaker_block(
    candles: Sequence[Candle],
    order_block: OrderBlock | None,
) -> BreakerBlock | None:
    """Turn an invalidated order block into a breaker after a closed-body break."""
    if order_block is None:
        return None

    for candle in candles:
        if candle.timestamp <= order_block.candle.timestamp:
            continue
        if order_block.direction is Direction.SELL and candle.close > order_block.high:
            return BreakerBlock(
                direction=Direction.BUY,
                low=order_block.low,
                high=order_block.high,
                source_order_block=order_block,
                break_time=candle.timestamp,
            )
        if order_block.direction is Direction.BUY and candle.close < order_block.low:
            return BreakerBlock(
                direction=Direction.SELL,
                low=order_block.low,
                high=order_block.high,
                source_order_block=order_block,
                break_time=candle.timestamp,
            )
    return None
