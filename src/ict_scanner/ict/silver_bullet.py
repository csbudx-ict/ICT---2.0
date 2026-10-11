from collections.abc import Sequence
from math import isfinite

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle


def detect_silver_bullet_fvg(candles: Sequence[Candle]) -> dict[str, float | str] | None:
    """Detect the latest closed three-candle FVG and map its retracement levels."""
    if len(candles) < 3:
        return None

    candle_1, _, candle_3 = candles[-3:]
    if any(
        candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None
        for candle in candles[-3:]
    ):
        raise ValueError("Silver Bullet candles must have timezone-aware timestamps")

    if candle_3.low > candle_1.high:
        direction = Direction.BUY
        low, high = candle_1.high, candle_3.low
        proximal, distal = high, low
    elif candle_3.high < candle_1.low:
        direction = Direction.SELL
        low, high = candle_3.high, candle_1.low
        proximal, distal = low, high
    else:
        return None

    if not all(isfinite(value) for value in (low, high)):
        return None

    midpoint = (low + high) / 2
    return {
        "direction": direction.value,
        "low": low,
        "high": high,
        "midpoint": midpoint,
        "retracement_entry": midpoint,
        "proximal_boundary": proximal,
        "distal_boundary": distal,
        "candle_1_timestamp": candle_1.timestamp.isoformat(),
        "timestamp": candle_3.timestamp.isoformat(),
    }
