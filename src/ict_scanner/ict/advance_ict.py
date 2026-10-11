from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle
from ict_scanner.ict.liquidity import build_liquidity_pools, detect_closed_candle_sweep


def _require_aware_candles(candles: Sequence[Candle]) -> None:
    if any(
        candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() is None
        for candle in candles
    ):
        raise ValueError("advanced ICT candles must have timezone-aware timestamps")


def _range_tolerance(candles: Sequence[Candle]) -> float:
    if not candles:
        return 0.0
    average_range = sum(candle.high - candle.low for candle in candles) / len(candles)
    return average_range * 0.1


def detect_inducement(
    candles: Sequence[Candle],
    direction: Direction,
    lookback: int = 30,
) -> dict[str, object] | None:
    """Return the latest confirmed internal swing opposing the directional move.

    Two closed candles on each side are required to confirm a swing. The latest
    candle is not considered a swing point; it is the current closed-candle context.
    """
    if lookback < 5:
        raise ValueError("lookback must be at least 5")
    if direction is Direction.NEUTRAL:
        return None
    _require_aware_candles(candles)
    if len(candles) < 6:
        return None

    first_index = max(2, len(candles) - lookback - 2)
    confirmed_history = candles[:-1]
    candidates: list[tuple[int, str, float]] = []
    for index in range(first_index, len(confirmed_history) - 2):
        candle = confirmed_history[index]
        neighbors = (*confirmed_history[index - 2 : index], *confirmed_history[index + 1 : index + 3])
        if direction is Direction.BUY and all(candle.low < other.low for other in neighbors):
            if candle.low < candles[-1].close:
                candidates.append((index, "SSL", candle.low))
        elif (
            direction is Direction.SELL
            and all(candle.high > other.high for other in neighbors)
            and candle.high > candles[-1].close
        ):
            candidates.append((index, "BSL", candle.high))

    if not candidates:
        return None
    index, pool_type, level = candidates[-1]
    return {
        "direction": direction.value,
        "pool_type": pool_type,
        "level": level,
        "source": "CONFIRMED_INTERNAL_SWING",
        "timestamp": confirmed_history[index].timestamp.isoformat(),
        "status": "RESTING_LIQUIDITY",
    }


def detect_turtle_soup(
    candles: Sequence[Candle],
    tolerance: float | None = None,
) -> dict[str, object] | None:
    """Detect a closed-candle sweep and reclaim of liquidity formed beforehand."""
    _require_aware_candles(candles)
    if tolerance is not None and (not isfinite(tolerance) or tolerance < 0):
        raise ValueError("tolerance must be finite and non-negative")
    if len(candles) < 4:
        return None
    history = candles[:-1]
    selected_tolerance = _range_tolerance(history) if tolerance is None else tolerance
    pools = build_liquidity_pools(history, selected_tolerance)
    sweep = detect_closed_candle_sweep(candles, pools)
    if sweep is None:
        return None
    return {
        "direction": "SELL" if sweep.pool.type == "BSL" else "BUY",
        "pool_type": sweep.pool.type,
        "pool_source": sweep.pool.source,
        "level": sweep.pool.price,
        "wick_extreme": sweep.wick_extreme,
        "stop_reference": sweep.wick_extreme,
        "timestamp": sweep.sweep_candle.timestamp.isoformat(),
    }


def detect_mitigation_block(
    candles: Sequence[Candle],
    lookback: int = 20,
    displacement_atr_multiplier: float = 1.5,
) -> dict[str, object] | None:
    """Detect a retest of the last opposing candle after a structural displacement.

    The retest must overlap the source candle and close on the displacement side
    of its 50% level. The source candle and displacement must precede the retest.
    """
    if lookback < 3:
        raise ValueError("lookback must be at least 3")
    if not isfinite(displacement_atr_multiplier) or displacement_atr_multiplier <= 0:
        raise ValueError("displacement_atr_multiplier must be finite and positive")
    _require_aware_candles(candles)
    if len(candles) < 5:
        return None

    retest = candles[-1]
    first_impulse = max(3, len(candles) - lookback - 1)
    for impulse_index in range(len(candles) - 2, first_impulse - 1, -1):
        impulse = candles[impulse_index]
        preceding = candles[max(0, impulse_index - 14) : impulse_index]
        if not preceding:
            continue
        average_range = sum(item.high - item.low for item in preceding) / len(preceding)
        if average_range <= 0 or abs(impulse.close - impulse.open) < (
            average_range * displacement_atr_multiplier
        ):
            continue
        preceding_high = max(item.high for item in preceding)
        preceding_low = min(item.low for item in preceding)
        if impulse.close > preceding_high:
            direction = Direction.BUY
        elif impulse.close < preceding_low:
            direction = Direction.SELL
        else:
            continue

        source_index = None
        for index in range(impulse_index - 1, max(-1, impulse_index - 6), -1):
            source_candle = candles[index]
            is_opposing = (
                source_candle.close < source_candle.open
                if direction is Direction.BUY
                else source_candle.close > source_candle.open
            )
            if is_opposing:
                source_index = index
                break
        if source_index is None:
            continue
        source = candles[source_index]
        midpoint = (source.low + source.high) / 2
        touched = retest.low <= source.high and retest.high >= source.low
        held = (
            retest.close >= midpoint
            if direction is Direction.BUY
            else retest.close <= midpoint
        )
        if not touched or not held:
            continue
        return {
            "direction": direction.value,
            "low": source.low,
            "high": source.high,
            "mean_threshold": midpoint,
            "entry": midpoint,
            "source_timestamp": source.timestamp.isoformat(),
            "displacement_timestamp": impulse.timestamp.isoformat(),
            "retest_timestamp": retest.timestamp.isoformat(),
        }
    return None


def detect_rejection_block(
    candles: Sequence[Candle],
    turtle_soup: Mapping[str, object] | None,
    minimum_wick_to_body: float = 1.5,
) -> dict[str, object] | None:
    """Map a dominant sweep wick into a rejection zone on the latest closed candle."""
    if not isfinite(minimum_wick_to_body) or minimum_wick_to_body <= 0:
        raise ValueError("minimum_wick_to_body must be finite and positive")
    _require_aware_candles(candles)
    if not candles or turtle_soup is None:
        return None
    candle = candles[-1]
    if turtle_soup.get("timestamp") != candle.timestamp.isoformat():
        return None

    body = abs(candle.close - candle.open)
    body_floor = max(body, (candle.high - candle.low) * 1e-9)
    lower_wick = min(candle.open, candle.close) - candle.low
    upper_wick = candle.high - max(candle.open, candle.close)
    direction_value = turtle_soup.get("direction")
    if direction_value == Direction.BUY.value and lower_wick >= body_floor * minimum_wick_to_body:
        return {
            "direction": Direction.BUY.value,
            "low": candle.low,
            "high": min(candle.open, candle.close),
            "wick_to_body": lower_wick / body_floor,
            "timestamp": candle.timestamp.isoformat(),
        }
    if direction_value == Direction.SELL.value and upper_wick >= body_floor * minimum_wick_to_body:
        return {
            "direction": Direction.SELL.value,
            "low": max(candle.open, candle.close),
            "high": candle.high,
            "wick_to_body": upper_wick / body_floor,
            "timestamp": candle.timestamp.isoformat(),
        }
    return None


def build_pd_arrays(
    *,
    fvg: Mapping[str, object] | None,
    order_block: Mapping[str, object] | None,
    breaker_block: Mapping[str, object] | None,
    ote: Mapping[str, object] | None,
    dealing_range: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    """Normalize active FVG, OB, breaker, and OTE zones against the dealing range."""
    if dealing_range is None:
        return []
    low_value = dealing_range.get("range_low")
    high_value = dealing_range.get("range_high")
    if not isinstance(low_value, (int, float)) or not isinstance(high_value, (int, float)):
        return []
    low, high = float(low_value), float(high_value)
    if not isfinite(low) or not isfinite(high) or high <= low:
        return []
    equilibrium = (low + high) / 2

    arrays: list[dict[str, object]] = []
    for name, zone in (
        ("FVG", fvg),
        ("ORDER_BLOCK", order_block),
        ("BREAKER_BLOCK", breaker_block),
        ("OTE", ote),
    ):
        if zone is None:
            continue
        zone_low = zone.get("low")
        zone_high = zone.get("high")
        if not isinstance(zone_low, (int, float)) or not isinstance(zone_high, (int, float)):
            continue
        if not isfinite(float(zone_low)) or not isfinite(float(zone_high)):
            continue
        if float(zone_high) < float(zone_low):
            continue
        midpoint = (float(zone_low) + float(zone_high)) / 2
        arrays.append(
            {
                "type": name,
                "low": float(zone_low),
                "high": float(zone_high),
                "midpoint": midpoint,
                "price_zone": (
                    "DISCOUNT"
                    if midpoint < equilibrium
                    else "PREMIUM" if midpoint > equilibrium else "EQUILIBRIUM"
                ),
                "direction": zone.get("direction"),
                "aligned": (
                    zone.get("direction") == Direction.BUY.value and midpoint < equilibrium
                )
                or (zone.get("direction") == Direction.SELL.value and midpoint > equilibrium),
            }
        )
    return arrays


def build_advanced_ict_analysis(
    candles: Sequence[Candle],
    direction: Direction,
    *,
    fvg: Mapping[str, object] | None,
    order_block: Mapping[str, object] | None,
    breaker_block: Mapping[str, object] | None,
    ote: Mapping[str, object] | None,
    dealing_range: Mapping[str, object] | None,
    killzone: str,
    killzone_valid: bool,
) -> dict[str, object]:
    """Collect the advanced detectors while reusing core scan structures."""
    turtle_soup = detect_turtle_soup(candles)
    return {
        "inducement": detect_inducement(candles, direction),
        "turtle_soup": turtle_soup,
        "mitigation_block": detect_mitigation_block(candles),
        "rejection_block": detect_rejection_block(candles, turtle_soup),
        "pd_arrays": build_pd_arrays(
            fvg=fvg,
            order_block=order_block,
            breaker_block=breaker_block,
            ote=ote,
            dealing_range=dealing_range,
        ),
        "killzone": {
            "session": killzone,
            "valid_entry_window": killzone_valid,
            "timestamp": candles[-1].timestamp.isoformat() if candles else None,
        },
    }
