from collections.abc import Sequence

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle, OrderBlock
from ict_scanner.ict.breaker_blocks import BreakerBlock, detect_breaker_block
from ict_scanner.ict.fractals import identify_swings
from ict_scanner.ict.imbalance import detect_fvg
from ict_scanner.ict.structure import detect_mss
from pandas import DataFrame


def _find_adjacent_breaker(
    candles: Sequence[Candle],
    impulse_index: int,
    direction: Direction,
    fvg_low: float,
    fvg_high: float,
) -> BreakerBlock | None:
    source_direction = Direction.SELL if direction is Direction.BUY else Direction.BUY
    history = candles[:impulse_index]
    matches: list[BreakerBlock] = []

    for source in history:
        is_opposing_candle = (
            source.close > source.open
            if source_direction is Direction.SELL
            else source.close < source.open
        )
        if not is_opposing_candle:
            continue

        order_block = OrderBlock(
            direction=source_direction,
            low=source.low,
            high=source.high,
            candle=source,
        )
        breaker = detect_breaker_block(history, order_block)
        if (
            breaker is not None
            and breaker.direction is direction
            and breaker.break_time < candles[impulse_index].timestamp
            and max(breaker.low, fvg_low) <= min(breaker.high, fvg_high)
        ):
            matches.append(breaker)

    return max(matches, key=lambda breaker: breaker.break_time) if matches else None


def detect_unicorn_setup(
    candles: Sequence[Candle],
    swing_frame: DataFrame,
    displacement_atr_multiplier: float,
) -> dict[str, object] | None:
    """Detect an MSS displacement FVG overlapping or touching a formed breaker."""
    if len(candles) < 17:
        return None
    if any(
        candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None
        for candle in candles
    ):
        raise ValueError("Unicorn candles must have timezone-aware timestamps")

    fvg_index = len(candles) - 1
    impulse_index = fvg_index - 1
    for direction in (Direction.BUY, Direction.SELL):
        fvg = detect_fvg(swing_frame, fvg_index, direction.value)
        if fvg is None:
            continue

        impulse_frame = identify_swings(swing_frame.iloc[: impulse_index + 1])
        mss = detect_mss(
            impulse_frame,
            impulse_index,
            direction.value,
            displacement_atr_multiplier,
        )
        if mss is None:
            continue

        breaker = _find_adjacent_breaker(
            candles,
            impulse_index,
            direction,
            fvg["fvg_low"],
            fvg["fvg_high"],
        )
        if breaker is None:
            continue

        return {
            "direction": direction.value,
            "breaker_low": breaker.low,
            "breaker_high": breaker.high,
            "breaker_formed_at": breaker.break_time.isoformat(),
            "fvg_low": fvg["fvg_low"],
            "fvg_high": fvg["fvg_high"],
            "fvg_midpoint": (fvg["fvg_low"] + fvg["fvg_high"]) / 2,
            "fvg_timestamp": candles[fvg_index].timestamp.isoformat(),
            "mss_level": float(mss["level"]),
            "displacement_atr": float(mss["displacement_atr"]),
            "mss_timestamp": candles[impulse_index].timestamp.isoformat(),
        }

    return None
