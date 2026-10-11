from collections.abc import Sequence

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle
from ict_scanner.ict.order_blocks import find_order_block
from ict_scanner.ict.structure import detect_mss
from pandas import DataFrame


def detect_institutional_order_block(
    candles: Sequence[Candle],
    swing_frame: DataFrame,
    displacement_atr_multiplier: float,
) -> dict[str, object] | None:
    """Find the last opposing candle before a displaced market-structure break."""
    if len(candles) < 15:
        return None
    if any(
        candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None
        for candle in candles
    ):
        raise ValueError("Institutional order-block candles must have timezone-aware timestamps")

    current = candles[-1]
    for direction in (Direction.BUY, Direction.SELL):
        mss = detect_mss(
            swing_frame,
            len(swing_frame) - 1,
            direction.value,
            displacement_atr_multiplier,
        )
        if mss is None:
            continue

        block = find_order_block(candles, direction, current.timestamp)
        if block is None:
            continue

        mean_threshold = (block.low + block.high) / 2
        return {
            "direction": direction.value,
            "low": block.low,
            "high": block.high,
            "mean_threshold": mean_threshold,
            "mitigation_entry": mean_threshold,
            "order_block_timestamp": block.candle.timestamp.isoformat(),
            "impulse_timestamp": current.timestamp.isoformat(),
            "mss_level": float(mss["level"]),
            "displacement_atr": float(mss["displacement_atr"]),
        }

    return None
