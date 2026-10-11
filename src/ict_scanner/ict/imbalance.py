from collections.abc import Sequence

import pandas as pd
from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import FVG, Candle


def detect_fvg(
    df: pd.DataFrame,
    current_idx: int,
    direction: str,
) -> dict[str, float] | None:
    """Detect a three-candle fair value gap at the selected closed candle."""
    if current_idx < 2 or current_idx >= len(df):
        return None

    candle_1 = df.iloc[current_idx - 2]
    candle_3 = df.iloc[current_idx]
    if direction == Direction.BUY.value and candle_3["Low"] > candle_1["High"]:
        return {
            "fvg_high": float(candle_3["Low"]),
            "fvg_low": float(candle_1["High"]),
        }
    if direction == Direction.SELL.value and candle_3["High"] < candle_1["Low"]:
        return {
            "fvg_high": float(candle_1["Low"]),
            "fvg_low": float(candle_3["High"]),
        }
    return None


def is_fvg_mitigated(candles: Sequence[Candle], fvg: FVG) -> bool:
    """Return whether a later closed candle has fully traded through the gap."""
    if fvg.creation_time.tzinfo is None or fvg.creation_time.utcoffset() is None:
        raise ValueError("FVG creation time must be timezone-aware")
    for candle in candles:
        if candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None:
            raise ValueError("FVG candles must have timezone-aware timestamps")
        if candle.timestamp <= fvg.creation_time:
            continue
        if fvg.direction is Direction.BUY and candle.low <= fvg.low:
            return True
        if fvg.direction is Direction.SELL and candle.high >= fvg.high:
            return True
    return False
