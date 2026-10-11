from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite

from ict_scanner.domain.models import Candle


@dataclass(frozen=True)
class PriceBox:
    low: float
    high: float
    equilibrium: float
    swept_side: str | None
    sweep_price: float | None


def detect_price_box(
    candles: Sequence[Candle],
    lookback: int = 12,
    max_range_atr: float = 2.0,
) -> PriceBox | None:
    """Detect a compact closed-candle range and any sweep of its resting liquidity.

    The final candle is used only as a possible sweep trigger; it never contributes to
    the box boundaries, which prevents the active candle from moving the range.
    """
    if lookback < 2:
        raise ValueError("lookback must be at least 2")
    if not isfinite(max_range_atr) or max_range_atr <= 0:
        raise ValueError("max_range_atr must be finite and positive")
    if len(candles) < lookback + 1:
        return None

    range_candles = candles[-lookback - 1 : -1]
    trigger = candles[-1]
    high = max(candle.high for candle in range_candles)
    low = min(candle.low for candle in range_candles)
    true_ranges = [
        max(
            candle.high - candle.low,
            abs(candle.high - previous.close),
            abs(candle.low - previous.close),
        )
        for previous, candle in pairwise(range_candles)
    ]
    average_true_range = sum(true_ranges) / len(true_ranges) if true_ranges else high - low
    if average_true_range <= 0 or high - low > average_true_range * max_range_atr:
        return None

    swept_side: str | None = None
    sweep_price: float | None = None
    if trigger.high > high and trigger.close < high:
        swept_side, sweep_price = "BSL", trigger.high
    elif trigger.low < low and trigger.close > low:
        swept_side, sweep_price = "SSL", trigger.low

    return PriceBox(
        low=low,
        high=high,
        equilibrium=(low + high) / 2,
        swept_side=swept_side,
        sweep_price=sweep_price,
    )
