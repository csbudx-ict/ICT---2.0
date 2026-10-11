import math
from collections.abc import Sequence
from datetime import UTC, datetime

import pandas as pd
from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import FVG, Candle
from ict_scanner.ict.engine import ICT_ENTRY_MODULES, ICT_MODULES, analyze_ict_modules
from ict_scanner.ict.imbalance import detect_fvg

DEMO_MODULES = (*ICT_MODULES, "master_sniper", *ICT_ENTRY_MODULES)


def build_demo_candle(index: int, previous_close: float, timestamp: datetime) -> Candle:
    if index < 0:
        raise ValueError("index must be non-negative")
    if not math.isfinite(previous_close) or previous_close <= 0:
        raise ValueError("previous_close must be a finite positive price")
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")

    timestamp = timestamp.astimezone(UTC)
    cycle_direction = 1 if (index // 12) % 2 == 0 else -1
    phase = index % 12
    if phase == 1:
        change = cycle_direction * 0.001
    elif phase == 2:
        change = cycle_direction * 0.00015
    else:
        change = math.sin(index * 0.7) * 0.00015

    open_price = previous_close
    close_price = open_price + change
    wick = 0.00008
    return Candle(
        timestamp=timestamp,
        open=open_price,
        high=max(open_price, close_price) + wick,
        low=min(open_price, close_price) - wick,
        close=close_price,
        volume=0.0,
    )


def detect_closed_candle_fvg(candles: Sequence[Candle]) -> FVG | None:
    if len(candles) < 3:
        return None

    latest = candles[-3:]
    frame = pd.DataFrame([{"High": candle.high, "Low": candle.low} for candle in latest])
    for direction in (Direction.BUY, Direction.SELL):
        gap = detect_fvg(frame, 2, direction.value)
        if gap is not None:
            return FVG(
                direction=direction,
                low=gap["fvg_low"],
                high=gap["fvg_high"],
                creation_time=latest[-1].timestamp,
            )
    return None


def analyze_demo_candles(candles: Sequence[Candle]) -> dict[str, object | None]:
    """Expose the deterministic ICT module calculations used by the demo stream."""
    return analyze_ict_modules(candles)
