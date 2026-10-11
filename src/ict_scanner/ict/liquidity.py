from collections.abc import Sequence
from datetime import UTC, date
from math import isfinite

import pandas as pd
from ict_scanner.domain.models import Candle, LiquidityPool, Sweep


def detect_liquidity_sweep(
    df: pd.DataFrame,
    current_idx: int,
) -> dict[str, str | float] | None:
    """Detect a wick through the latest confirmed swing high or low."""
    if current_idx < 0 or current_idx >= len(df):
        return None
    row = df.iloc[current_idx]
    previous = df.iloc[:current_idx]

    recent_highs = previous[previous["Swing_High"] == True]
    if not recent_highs.empty:
        level = recent_highs.iloc[-1]["Swing_High_Price"]
        if row["High"] > level and row["Close"] < level:
            return {"type": "BSL_SWEEP", "level": float(level), "direction": "SELL"}

    recent_lows = previous[previous["Swing_Low"] == True]
    if not recent_lows.empty:
        level = recent_lows.iloc[-1]["Swing_Low_Price"]
        if row["Low"] < level and row["Close"] > level:
            return {"type": "SSL_SWEEP", "level": float(level), "direction": "BUY"}
    return None


def find_equal_liquidity_pools(
    candles: Sequence[Candle],
    tolerance: float,
) -> list[LiquidityPool]:
    """Find equal highs/lows no farther apart than the supplied price tolerance."""
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and non-negative")

    pools: list[LiquidityPool] = []
    seen: set[tuple[str, float]] = set()
    for index, candle in enumerate(candles):
        for previous in candles[:index]:
            for price, prior_price, side in (
                (candle.high, previous.high, "HIGH"),
                (candle.low, previous.low, "LOW"),
            ):
                if abs(price - prior_price) > tolerance:
                    continue
                level = (price + prior_price) / 2
                source = "EQH" if side == "HIGH" else "EQL"
                key = (source, round(level, 10))
                if key in seen:
                    continue
                seen.add(key)
                pools.append(
                    LiquidityPool(
                        type="BSL" if side == "HIGH" else "SSL",
                        price=level,
                        source=source,
                        timestamp=candle.timestamp,
                    )
                )
    return pools


def detect_closed_candle_sweep(
    candles: Sequence[Candle],
    pools: Sequence[LiquidityPool],
) -> Sweep | None:
    """Detect a wick through a prior pool that closes back on its unswept side."""
    if not candles:
        return None
    candle = candles[-1]
    for pool in reversed(pools):
        if pool.timestamp >= candle.timestamp:
            continue
        if pool.type == "BSL" and candle.high > pool.price and candle.close < pool.price:
            return Sweep(pool=pool, wick_extreme=candle.high, sweep_candle=candle)
        if pool.type == "SSL" and candle.low < pool.price and candle.close > pool.price:
            return Sweep(pool=pool, wick_extreme=candle.low, sweep_candle=candle)
    return None


def build_liquidity_pools(
    candles: Sequence[Candle],
    tolerance: float,
) -> list[LiquidityPool]:
    """Collect confirmed swings, equal levels, prior-day/week levels, and Asian range."""
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and non-negative")
    if any(
        candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None
        for candle in candles
    ):
        raise ValueError("liquidity candles must have timezone-aware timestamps")
    if not candles:
        return []

    pools = find_equal_liquidity_pools(candles, tolerance)
    for index in range(2, len(candles) - 2):
        candle = candles[index]
        neighbors = (*candles[index - 2 : index], *candles[index + 1 : index + 3])
        if all(candle.high > other.high for other in neighbors):
            pools.append(
                LiquidityPool(
                    type="BSL",
                    price=candle.high,
                    source="SWING",
                    timestamp=candle.timestamp,
                )
            )
        if all(candle.low < other.low for other in neighbors):
            pools.append(
                LiquidityPool(
                    type="SSL",
                    price=candle.low,
                    source="SWING",
                    timestamp=candle.timestamp,
                )
            )

    candles_by_day: dict[date, list[Candle]] = {}
    for candle in candles:
        day = candle.timestamp.astimezone(UTC).date()
        candles_by_day.setdefault(day, []).append(candle)
    current_day = max(candles_by_day)
    prior_days = [day for day in candles_by_day if day < current_day]
    if prior_days:
        previous_day = candles_by_day[max(prior_days)]
        last_timestamp = max(candle.timestamp for candle in previous_day)
        pools.extend(
            (
                LiquidityPool(
                    type="BSL",
                    price=max(candle.high for candle in previous_day),
                    source="PDH",
                    timestamp=last_timestamp,
                ),
                LiquidityPool(
                    type="SSL",
                    price=min(candle.low for candle in previous_day),
                    source="PDL",
                    timestamp=last_timestamp,
                ),
            )
        )

    current_week = current_day.isocalendar()[:2]
    candles_by_week: dict[tuple[int, int], list[Candle]] = {}
    for candle in candles:
        week = candle.timestamp.astimezone(UTC).date().isocalendar()[:2]
        candles_by_week.setdefault(week, []).append(candle)
    prior_weeks = [week for week in candles_by_week if week < current_week]
    if prior_weeks:
        previous_week = candles_by_week[max(prior_weeks)]
        last_timestamp = max(candle.timestamp for candle in previous_week)
        pools.extend(
            (
                LiquidityPool(
                    type="BSL",
                    price=max(candle.high for candle in previous_week),
                    source="PWH",
                    timestamp=last_timestamp,
                ),
                LiquidityPool(
                    type="SSL",
                    price=min(candle.low for candle in previous_week),
                    source="PWL",
                    timestamp=last_timestamp,
                ),
            )
        )

    asian_candles = [
        candle
        for candle in candles_by_day[current_day]
        if candle.timestamp.astimezone(UTC).hour < 6
    ]
    if asian_candles:
        last_timestamp = max(candle.timestamp for candle in asian_candles)
        pools.extend(
            (
                LiquidityPool(
                    type="BSL",
                    price=max(candle.high for candle in asian_candles),
                    source="ASIAN_HIGH",
                    timestamp=last_timestamp,
                ),
                LiquidityPool(
                    type="SSL",
                    price=min(candle.low for candle in asian_candles),
                    source="ASIAN_LOW",
                    timestamp=last_timestamp,
                ),
            )
        )
    return pools
