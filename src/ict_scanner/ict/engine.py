from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime

import pandas as pd
from ict_scanner.config.settings import settings
from ict_scanner.domain.enums import Direction, Timeframe
from ict_scanner.domain.models import FVG, Candle, Sweep
from ict_scanner.ict.advance_ict import build_advanced_ict_analysis
from ict_scanner.ict.box_liquidity import detect_price_box
from ict_scanner.ict.breaker_blocks import detect_breaker_block
from ict_scanner.ict.fibonacci import get_fib_levels, get_ote_sweet_spot, get_ote_zone, is_in_ote
from ict_scanner.ict.fractals import identify_swings
from ict_scanner.ict.imbalance import detect_fvg, is_fvg_mitigated
from ict_scanner.ict.institutional_order_block import detect_institutional_order_block
from ict_scanner.ict.killzones import get_active_killzone, is_valid_killzone
from ict_scanner.ict.levels import calculate_rr
from ict_scanner.ict.liquidity import (
    build_liquidity_pools,
    detect_closed_candle_sweep,
)
from ict_scanner.ict.order_blocks import find_order_block
from ict_scanner.ict.premium_discount import (
    get_dealing_range,
    get_price_zone,
    validate_pd_alignment,
)
from ict_scanner.ict.scoring import calculate_confluence_score
from ict_scanner.ict.silver_bullet import detect_silver_bullet_fvg
from ict_scanner.ict.structure import detect_mss
from ict_scanner.ict.unicorn import detect_unicorn_setup

ICT_MODULES = (
    "fvg",
    "order_blocks",
    "ote_fibonacci",
    "breaker_blocks",
    "premium_discount",
    "box_liquidity",
)
ICT_ENTRY_MODULES = (
    "unicorn_setup",
    "silver_bullet_fvg",
    "institutional_order_block",
)


def _as_frame(candles: Sequence[Candle]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [candle.open for candle in candles],
            "High": [candle.high for candle in candles],
            "Low": [candle.low for candle in candles],
            "Close": [candle.close for candle in candles],
            "Volume": [candle.volume for candle in candles],
        },
        index=[candle.timestamp for candle in candles],
    )


def _serialize_sweep(sweep: Sweep | None) -> dict[str, object] | None:
    if sweep is None:
        return None
    return {
        "direction": "SELL" if sweep.pool.type == "BSL" else "BUY",
        "pool_type": sweep.pool.source,
        "level": sweep.pool.price,
        "wick_extreme": sweep.wick_extreme,
        "timestamp": sweep.sweep_candle.timestamp.isoformat(),
    }


def analyze_ict_modules(candles: Sequence[Candle]) -> dict[str, object | None]:
    """Calculate closed-candle ICT features for the live demo and scanner."""
    empty: dict[str, object | None] = {
        **{module: None for module in ICT_MODULES},
        **{module: None for module in ICT_ENTRY_MODULES},
        "liquidity_sweep": None,
        "mss": None,
        "master_sniper": None,
        "advanced_ict": None,
    }
    if len(candles) < 3:
        return empty

    current = candles[-1]
    frame = identify_swings(_as_frame(candles))
    fvg_values = None
    fvg_direction: Direction | None = None
    fvg_timestamp = None
    fvg_index = None
    start_index = max(2, len(candles) - 20)
    for index in range(len(candles) - 1, start_index - 1, -1):
        for candidate_direction in (Direction.BUY, Direction.SELL):
            candidate = detect_fvg(frame, index, candidate_direction.value)
            if candidate is None:
                continue
            candidate_fvg = FVG(
                direction=candidate_direction,
                low=candidate["fvg_low"],
                high=candidate["fvg_high"],
                creation_time=candles[index].timestamp,
            )
            if is_fvg_mitigated(candles[index + 1 :], candidate_fvg):
                continue
            fvg_values = candidate
            fvg_direction = candidate_direction
            fvg_timestamp = candles[index].timestamp
            fvg_index = index
            break
        if fvg_values is not None:
            break

    entry = current.close
    fvg_signal: dict[str, object] | None = None
    if fvg_values is not None and fvg_direction is not None and fvg_timestamp is not None:
        entry = (fvg_values["fvg_low"] + fvg_values["fvg_high"]) / 2
        fvg_signal = {
            "direction": fvg_direction.value,
            "low": fvg_values["fvg_low"],
            "high": fvg_values["fvg_high"],
            "midpoint": entry,
            "timestamp": fvg_timestamp.isoformat(),
            "mitigated": False,
        }

    direction = fvg_direction or (
        Direction.BUY if current.close >= candles[-3].close else Direction.SELL
    )
    displacement_time = (
        candles[fvg_index - 1].timestamp
        if fvg_index is not None and fvg_index > 0
        else current.timestamp
    )
    order_block = find_order_block(candles, direction, displacement_time)
    order_block_signal = (
        {
            "direction": order_block.direction.value,
            "low": order_block.low,
            "high": order_block.high,
            "open": order_block.candle.open,
            "timestamp": order_block.candle.timestamp.isoformat(),
        }
        if order_block is not None
        else None
    )

    range_candles = candles[-min(len(candles), 20) :]
    range_low = min(candle.low for candle in range_candles)
    range_high = max(candle.high for candle in range_candles)
    range_low, range_high, equilibrium = get_dealing_range(range_low, range_high)
    ote_low, ote_high = get_ote_zone(range_low, range_high, direction)
    sweet_spot = get_ote_sweet_spot(range_low, range_high, direction)
    ote_signal = {
        "direction": direction.value,
        "low": ote_low,
        "high": ote_high,
        "sweet_spot_0_705": sweet_spot,
        "entry": entry,
        "entry_inside": is_in_ote(entry, ote_low, ote_high),
        "price_inside": is_in_ote(current.close, ote_low, ote_high),
    }

    pd_signal = {
        "equilibrium": equilibrium,
        "price_zone": get_price_zone(current.close, range_low, range_high),
        "entry_zone": get_price_zone(entry, range_low, range_high),
        "aligned": validate_pd_alignment(entry, equilibrium, direction),
        "range_low": range_low,
        "range_high": range_high,
        "direction": direction.value,
    }

    breaker = detect_breaker_block(candles, order_block)
    breaker_signal = (
        {
            "direction": breaker.direction.value,
            "low": breaker.low,
            "high": breaker.high,
            "break_time": breaker.break_time.isoformat(),
        }
        if breaker is not None
        else None
    )

    average_range = sum(candle.high - candle.low for candle in range_candles) / len(range_candles)
    pools = build_liquidity_pools(candles[:-1], tolerance=average_range * 0.1)
    box = detect_price_box(candles)
    recent_pools = sorted(pools, key=lambda pool: pool.timestamp, reverse=True)[:8]
    box_signal: dict[str, object] = {
        "low": box.low if box is not None else None,
        "high": box.high if box is not None else None,
        "equilibrium": box.equilibrium if box is not None else None,
        "swept_side": box.swept_side if box is not None else None,
        "sweep_price": box.sweep_price if box is not None else None,
        "consolidating": box is not None,
        "liquidity_pools": [
            {
                "type": pool.type,
                "source": pool.source,
                "price": pool.price,
                "timestamp": pool.timestamp.isoformat(),
            }
            for pool in recent_pools
        ],
    }
    sweep = detect_closed_candle_sweep(candles, pools)
    sweep_signal = _serialize_sweep(sweep)

    mss_values = detect_mss(
        frame,
        len(frame) - 1,
        direction.value,
        settings.displacement_atr_multiplier,
    )
    mss_signal = (
        {
            "direction": direction.value,
            "level": float(mss_values["level"]),
            "displacement_atr": float(mss_values["displacement_atr"]),
            "timestamp": current.timestamp.isoformat(),
        }
        if mss_values is not None
        else None
    )
    empty["unicorn_setup"] = detect_unicorn_setup(
        candles,
        frame,
        settings.displacement_atr_multiplier,
    )
    empty["silver_bullet_fvg"] = detect_silver_bullet_fvg(candles)
    empty["institutional_order_block"] = detect_institutional_order_block(
        candles,
        frame,
        settings.displacement_atr_multiplier,
    )
    session = get_active_killzone(current.timestamp)
    overlap = bool(
        order_block is not None
        and fvg_values is not None
        and max(order_block.low, fvg_values["fvg_low"])
        <= min(order_block.high, fvg_values["fvg_high"])
    )
    expected_sweep = "SSL" if direction is Direction.BUY else "BSL"
    confluences = {
        "fvg": fvg_signal is not None,
        "order_block_overlap": overlap,
        "ote_entry": bool(ote_signal["entry_inside"]),
        "breaker_block": breaker is not None and breaker.direction is direction,
        "premium_discount": bool(pd_signal["aligned"]),
        "box_liquidity_sweep": box is not None and box.swept_side == expected_sweep,
        "liquidity_sweep": (
            sweep is not None
            and (
                sweep.pool.type == "SSL" if direction is Direction.BUY else sweep.pool.type == "BSL"
            )
        ),
        "mss_displacement": mss_signal is not None,
        "killzone": is_valid_killzone(session),
    }
    sweep_type = sweep.pool.source if sweep is not None else ""
    score = calculate_confluence_score(
        htf_aligned=False,
        pool_type=sweep_type,
        displacement_atr=float(mss_values["displacement_atr"]) if mss_values else 0.0,
        pd_aligned=bool(pd_signal["aligned"]),
        in_ote=bool(ote_signal["entry_inside"]),
        has_ob=overlap,
        in_killzone=is_valid_killzone(session),
        rr2=0.0,
        has_clear_target=False,
    )
    empty["fvg"] = fvg_signal
    empty["order_blocks"] = order_block_signal
    empty["ote_fibonacci"] = ote_signal
    empty["breaker_blocks"] = breaker_signal
    empty["premium_discount"] = pd_signal
    empty["box_liquidity"] = box_signal
    empty["liquidity_sweep"] = sweep_signal
    empty["mss"] = mss_signal
    empty["master_sniper"] = {
        "direction": direction.value,
        "ready": all(confluences.values()),
        "score": score,
        "confluences": confluences,
        "entry": entry,
        "stop_reference": sweep.wick_extreme if sweep is not None else None,
        "timestamp": current.timestamp.isoformat(),
    }
    empty["advanced_ict"] = build_advanced_ict_analysis(
        candles,
        direction,
        fvg=fvg_signal,
        order_block=order_block_signal,
        breaker_block=breaker_signal,
        ote=ote_signal,
        dealing_range=pd_signal,
        killzone=session.value,
        killzone_valid=is_valid_killzone(session),
    )
    return empty


def scan_for_setups(
    symbol: str,
    candles: Sequence[Candle],
    timeframe: Timeframe = Timeframe.M5,
) -> list[dict[str, object]]:
    """Return a trade plan only when the complete master-sniper confluence is present."""
    enabled_modules = set(settings.enabled_ict_modules)
    if "master_sniper" not in enabled_modules or not set(ICT_MODULES).issubset(enabled_modules):
        return []
    if len(candles) < 20:
        return []
    analysis = analyze_ict_modules(candles)
    sniper = analysis["master_sniper"]
    fvg = analysis["fvg"]
    if not isinstance(sniper, dict) or not isinstance(fvg, dict) or sniper.get("ready") is not True:
        return []

    direction_value = sniper.get("direction")
    entry_value = sniper.get("entry")
    stop_value = sniper.get("stop_reference")
    timestamp_value = sniper.get("timestamp")
    range_value = analysis["premium_discount"]
    if (
        not isinstance(direction_value, str)
        or not isinstance(entry_value, (int, float))
        or not isinstance(stop_value, (int, float))
        or not isinstance(timestamp_value, str)
        or not isinstance(range_value, dict)
    ):
        return []
    direction = Direction(direction_value)
    entry = float(entry_value)
    stop_reference = float(stop_value)
    initial_risk = abs(entry - stop_reference)
    if initial_risk == 0:
        return []
    stop_loss = (
        stop_reference - initial_risk * 0.25
        if direction is Direction.BUY
        else stop_reference + initial_risk * 0.25
    )
    risk = abs(entry - stop_loss)
    range_low_value = range_value.get("range_low")
    range_high_value = range_value.get("range_high")
    if not isinstance(range_low_value, (int, float)) or not isinstance(
        range_high_value, (int, float)
    ):
        return []
    range_low = float(range_low_value)
    range_high = float(range_high_value)
    fib_levels = get_fib_levels(range_low, range_high, direction)
    minimum_rr = max(settings.min_rr, 2.0)
    tp1 = entry + (risk * minimum_rr if direction is Direction.BUY else -risk * minimum_rr)
    extension = fib_levels[-0.27]
    tp2 = (
        max(extension, entry + risk * 3)
        if direction is Direction.BUY
        else min(extension, entry - risk * 3)
    )
    rr1 = calculate_rr(entry, stop_loss, tp1)
    rr2 = calculate_rr(entry, stop_loss, tp2)
    timestamp = datetime.fromisoformat(timestamp_value)
    dedupe = hashlib.sha256(
        f"{symbol}|{direction.value}|{entry:.8f}|{timestamp.isoformat()}".encode()
    ).hexdigest()
    return [
        {
            "symbol": symbol,
            "direction": direction.value,
            "timeframe": timeframe.value,
            "entry_price": entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "rr1": rr1,
            "rr2": rr2,
            "fvg_low": fvg.get("low"),
            "fvg_high": fvg.get("high"),
            "rule_score": sniper.get("score"),
            "dedupe_key": dedupe,
            "created_at": timestamp.isoformat(),
        }
    ]
