from datetime import UTC, datetime, timedelta

import pytest

from ict_scanner.domain.enums import Direction, Timeframe
from ict_scanner.domain.models import FVG, Candle, OrderBlock
from ict_scanner.ict.box_liquidity import detect_price_box
from ict_scanner.ict.breaker_blocks import detect_breaker_block
from ict_scanner.ict.engine import analyze_ict_modules, scan_for_setups
from ict_scanner.ict.fibonacci import (
    FIBONACCI_LEVELS,
    get_fib_levels,
    get_ote_sweet_spot,
    get_ote_zone,
    is_in_ote,
)
from ict_scanner.ict.imbalance import is_fvg_mitigated
from ict_scanner.ict.levels import calculate_levels, calculate_rr
from ict_scanner.ict.liquidity import (
    build_liquidity_pools,
    detect_closed_candle_sweep,
    find_equal_liquidity_pools,
)
from ict_scanner.ict.order_blocks import find_order_block
from ict_scanner.ict.premium_discount import (
    get_dealing_range,
    get_price_zone,
    validate_pd_alignment,
)


def candle(
    index: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1,
    )


def test_ote_zones_follow_the_retracement_direction_and_include_sweet_spot() -> None:
    bullish_zone = get_ote_zone(100, 200, Direction.BUY)
    bearish_zone = get_ote_zone(100, 200, Direction.SELL)

    assert bullish_zone == pytest.approx((121.0, 138.2))
    assert bearish_zone == pytest.approx((161.8, 179.0))
    assert get_ote_sweet_spot(100, 200, Direction.BUY) == pytest.approx(129.5)
    assert get_ote_sweet_spot(100, 200, Direction.SELL) == pytest.approx(170.5)
    assert is_in_ote(129.5, *bullish_zone)


def test_fibonacci_levels_match_the_requested_order_and_values() -> None:
    assert FIBONACCI_LEVELS == (0, 1, 0.618, 0.705, 0.79, -1, -0.62, -0.27, 0.5)
    assert tuple(get_fib_levels(100, 200)) == FIBONACCI_LEVELS
    assert get_fib_levels(100, 200)[0.705] == pytest.approx(129.5)


@pytest.mark.parametrize(("low", "high"), [(1, 1), (2, 1), (float("nan"), 2)])
def test_ote_rejects_invalid_ranges(low: float, high: float) -> None:
    with pytest.raises(ValueError):
        get_ote_zone(low, high, Direction.BUY)


def test_ote_rejects_neutral_direction() -> None:
    with pytest.raises(ValueError, match="BUY or SELL"):
        get_ote_zone(100, 200, Direction.NEUTRAL)


def test_premium_discount_equilibrium_is_an_explicit_middle_zone() -> None:
    assert get_dealing_range(10, 20) == (10, 20, 15)
    assert get_price_zone(14, 10, 20) == "DISCOUNT"
    assert get_price_zone(15, 10, 20) == "EQUILIBRIUM"
    assert get_price_zone(16, 10, 20) == "PREMIUM"
    assert not validate_pd_alignment(15, 15, Direction.BUY)
    assert validate_pd_alignment(14, 15, Direction.BUY)
    assert validate_pd_alignment(16, 15, Direction.SELL)
    assert not validate_pd_alignment(16, 15, Direction.NEUTRAL)


def test_order_block_finds_last_opposite_candle_before_displacement() -> None:
    candles = [
        candle(0, 10.0, 10.5, 9.5, 10.2),
        candle(1, 10.2, 10.4, 9.8, 10.0),
        candle(2, 10.0, 11.0, 10.0, 10.9),
    ]

    block = find_order_block(candles, Direction.BUY, candles[-1].timestamp)

    assert block is not None
    assert block.candle is candles[1]
    assert (block.low, block.high) == (9.8, 10.4)


@pytest.mark.parametrize(
    ("direction", "fvg_low", "fvg_high", "ob_low", "ob_high", "sweep", "expected_side"),
    [
        (Direction.BUY, 125, 133, 124, 134, 120, "BUY"),
        (Direction.SELL, 167, 175, 166, 176, 180, "SELL"),
    ],
)
def test_trade_levels_prefer_fvg_order_block_overlap_and_keep_targets_directional(
    direction: Direction,
    fvg_low: float,
    fvg_high: float,
    ob_low: float,
    ob_high: float,
    sweep: float,
    expected_side: str,
) -> None:
    block_candle = candle(0, (ob_low + ob_high) / 2, ob_high, ob_low, ob_low)
    fvg = FVG(direction, fvg_low, fvg_high, candle(1, 130, 135, 125, 132).timestamp)
    block = OrderBlock(direction, ob_low, ob_high, block_candle)

    entry, stop, tp1, tp2 = calculate_levels(
        direction,
        sweep,
        fvg,
        block,
        1,
        {
            0.618: 138.2 if direction is Direction.BUY else 161.8,
            0.786: 121.4 if direction is Direction.BUY else 178.6,
            -0.27: 227.0 if direction is Direction.BUY else 73.0,
        },
    )

    assert expected_side == direction.value
    assert max(fvg_low, ob_low, 121.4 if direction is Direction.BUY else 161.8) <= entry
    assert entry <= min(fvg_high, ob_high, 138.2 if direction is Direction.BUY else 178.6)
    assert (stop < entry < tp1 < tp2) if direction is Direction.BUY else (tp2 < tp1 < entry < stop)
    assert calculate_rr(entry, stop, tp1) == pytest.approx(2.0)


def test_trade_levels_reject_a_neutral_direction() -> None:
    source = candle(0, 10, 11, 9, 10)
    with pytest.raises(ValueError, match="BUY or SELL"):
        calculate_levels(
            Direction.NEUTRAL,
            9,
            FVG(Direction.BUY, 10, 11, source.timestamp),
            None,
            0.1,
            {0.618: 10.2, 0.786: 10.1, -0.27: 12},
        )


@pytest.mark.parametrize(
    ("block_direction", "break_close", "expected_direction"),
    [
        (Direction.SELL, 11.1, Direction.BUY),
        (Direction.BUY, 9.4, Direction.SELL),
    ],
)
def test_invalidated_order_block_becomes_a_breaker(
    block_direction: Direction,
    break_close: float,
    expected_direction: Direction,
) -> None:
    source = candle(0, 10.0, 11.0, 9.0, 10.0)
    block = OrderBlock(
        direction=block_direction,
        low=9.5,
        high=10.5,
        candle=source,
    )

    breaker = detect_breaker_block([source, candle(1, 10.0, 11.2, 8.8, break_close)], block)

    assert breaker is not None
    assert breaker.direction is expected_direction
    assert breaker.low == block.low
    assert breaker.high == block.high


def test_unbroken_order_block_does_not_form_a_breaker() -> None:
    source = candle(0, 10.0, 11.0, 9.0, 10.0)
    block = OrderBlock(Direction.SELL, 9.5, 10.5, source)

    assert detect_breaker_block([source, candle(1, 10.0, 10.4, 9.8, 10.1)], block) is None


def test_box_detects_boundary_liquidity_sweep_without_moving_box_bounds() -> None:
    candles = [
        candle(0, 10.2, 11.0, 10.0, 10.4),
        candle(1, 10.4, 10.9, 10.1, 10.3),
        candle(2, 10.3, 10.8, 10.0, 10.5),
        candle(3, 10.5, 10.9, 10.2, 10.4),
        candle(4, 10.7, 11.2, 10.3, 10.8),
    ]

    box = detect_price_box(candles, lookback=4, max_range_atr=2.0)

    assert box is not None
    assert (box.low, box.high) == (10.0, 11.0)
    assert box.equilibrium == 10.5
    assert box.swept_side == "BSL"
    assert box.sweep_price == 11.2


def test_box_needs_closed_range_and_validates_configuration() -> None:
    assert detect_price_box([candle(0, 1, 2, 0, 1)], lookback=2) is None
    with pytest.raises(ValueError):
        detect_price_box([], lookback=1)
    with pytest.raises(ValueError):
        detect_price_box([], max_range_atr=0)


def test_equal_liquidity_pools_and_closed_candle_sweep() -> None:
    candles = [
        candle(0, 10.2, 11.0, 10.0, 10.4),
        candle(1, 10.3, 11.02, 10.1, 10.5),
        candle(2, 10.5, 11.2, 10.2, 10.8),
    ]

    pools = find_equal_liquidity_pools(candles[:2], tolerance=0.03)
    sweep = detect_closed_candle_sweep(candles, pools)

    assert any(pool.source == "EQH" for pool in pools)
    assert sweep is not None
    assert sweep.pool.type == "BSL"
    assert sweep.wick_extreme == 11.2


def test_liquidity_builder_includes_prior_day_week_and_asian_levels() -> None:
    candles = [
        Candle(datetime(2026, 1, 2, 12, tzinfo=UTC), 10, 12, 8, 11, 1),
        Candle(datetime(2026, 1, 4, 3, tzinfo=UTC), 10, 11, 9, 10.5, 1),
        Candle(datetime(2026, 1, 4, 8, tzinfo=UTC), 10, 10.5, 9.5, 10, 1),
        Candle(datetime(2026, 1, 5, 3, tzinfo=UTC), 10, 11.2, 9.2, 10.5, 1),
        Candle(datetime(2026, 1, 5, 8, tzinfo=UTC), 10, 10.5, 9.5, 10, 1),
    ]

    pools = build_liquidity_pools(candles, tolerance=0.01)
    sources = {pool.source for pool in pools}

    assert {"PDH", "PDL", "PWH", "PWL", "ASIAN_HIGH", "ASIAN_LOW"} <= sources
    assert next(pool.price for pool in pools if pool.source == "PDH") == 11
    assert next(pool.price for pool in pools if pool.source == "PDL") == 9
    assert next(pool.price for pool in pools if pool.source == "ASIAN_HIGH") == 11.2
    assert next(pool.price for pool in pools if pool.source == "ASIAN_LOW") == 9.2


def test_liquidity_builder_requires_timezone_aware_candles() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_liquidity_pools(
            [Candle(datetime.fromisoformat("2026-01-01"), 10, 11, 9, 10, 1)],
            tolerance=0.01,
        )


def test_fvg_mitigation_uses_only_subsequent_closed_candles() -> None:
    created = candle(1, 10.5, 11.0, 10.5, 10.9)
    fvg = FVG(Direction.BUY, 10.0, 10.5, created.timestamp)
    before_fill = [created, candle(2, 10.8, 11.0, 10.1, 10.7)]
    after_fill = [*before_fill, candle(3, 10.4, 10.7, 9.9, 10.2)]

    assert not is_fvg_mitigated(before_fill, fvg)
    assert is_fvg_mitigated(after_fill, fvg)


def test_engine_returns_all_module_slots_for_short_candle_windows() -> None:
    analysis = analyze_ict_modules([candle(0, 10, 11, 9, 10)])

    assert set(analysis) == {
        "fvg",
        "order_blocks",
        "ote_fibonacci",
        "breaker_blocks",
        "premium_discount",
        "box_liquidity",
        "unicorn_setup",
        "silver_bullet_fvg",
        "institutional_order_block",
        "liquidity_sweep",
        "mss",
        "master_sniper",
        "advanced_ict",
    }
    assert all(value is None for value in analysis.values())
    assert scan_for_setups("EUR/USD", [], Timeframe.M5) == []


def test_engine_calculates_modules_on_a_closed_candle_window() -> None:
    candles = [
        candle(
            index,
            10 + index * 0.001,
            10.02 + index * 0.001,
            9.99 + index * 0.001,
            10.01 + index * 0.001,
        )
        for index in range(20)
    ]

    analysis = analyze_ict_modules(candles)

    assert analysis["ote_fibonacci"] is not None
    assert analysis["premium_discount"] is not None
    assert analysis["master_sniper"] is not None
    assert "ready" in analysis["master_sniper"]
    assert analysis["advanced_ict"] is not None
    assert scan_for_setups("EUR/USD", candles, Timeframe.M5) == []


def test_rr_is_zero_for_zero_risk() -> None:
    assert calculate_rr(10, 10, 12) == 0
