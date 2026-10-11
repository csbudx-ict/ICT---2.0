from datetime import UTC, datetime, timedelta

import pytest

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle
from ict_scanner.ict.advance_ict import (
    build_pd_arrays,
    detect_inducement,
    detect_mitigation_block,
    detect_rejection_block,
    detect_turtle_soup,
)
from ict_scanner.ict.backtesting import backtest_turtle_soup


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
        volume=1.0,
    )


def test_inducement_uses_confirmed_internal_swing_and_ignores_trigger_as_pivot() -> None:
    candles = [
        candle(0, 10, 10.5, 9.5, 10),
        candle(1, 10, 10.4, 9.4, 10),
        candle(2, 10, 10.3, 8.0, 9.8),
        candle(3, 9.8, 10.2, 9.2, 10),
        candle(4, 10, 10.5, 9.7, 10.2),
        candle(5, 10.2, 10.6, 10.0, 10.4),
        candle(6, 10.4, 10.8, 10.2, 10.7),
    ]

    result = detect_inducement(candles, Direction.BUY)

    assert result is not None
    assert result["level"] == 8.0
    assert result["pool_type"] == "SSL"
    assert result["timestamp"] == candles[2].timestamp.isoformat()
    assert result["status"] == "RESTING_LIQUIDITY"


def test_turtle_soup_requires_a_reclaim_of_previously_formed_liquidity() -> None:
    candles = [
        candle(0, 10.4, 11.0, 10.0, 10.5),
        candle(1, 10.5, 11.01, 10.1, 10.7),
        candle(2, 10.7, 10.9, 10.2, 10.4),
        candle(3, 10.4, 10.8, 10.1, 10.5),
        candle(4, 10.5, 11.2, 10.3, 10.8),
    ]

    result = detect_turtle_soup(candles)

    assert result is not None
    assert result["direction"] == Direction.SELL.value
    assert result["pool_type"] == "BSL"
    assert result["timestamp"] == candles[-1].timestamp.isoformat()
    assert result["stop_reference"] == candles[-1].high
    assert detect_turtle_soup(candles[:-1]) is None


def test_rejection_block_maps_only_a_dominant_sweep_wick() -> None:
    sweep_candle = candle(4, 11.0, 11.5, 10.8, 10.9)
    soup = {"direction": "SELL", "timestamp": sweep_candle.timestamp.isoformat()}

    result = detect_rejection_block([sweep_candle], soup)

    assert result is not None
    assert result["direction"] == Direction.SELL.value
    assert result["low"] == 11.0
    assert result["high"] == 11.5
    assert result["wick_to_body"] == pytest.approx(5.0)
    assert detect_rejection_block([sweep_candle], None) is None


def test_mitigation_block_requires_later_retest_after_displacement() -> None:
    candles = [
        candle(0, 10.0, 10.2, 9.9, 10.1),
        candle(1, 10.1, 10.3, 10.0, 10.2),
        candle(2, 10.2, 10.4, 10.1, 10.3),
        candle(3, 10.3, 10.5, 10.2, 10.4),
        candle(4, 10.4, 10.45, 10.0, 10.1),
        candle(5, 10.1, 11.2, 10.05, 11.0),
        candle(6, 10.2, 10.4, 10.05, 10.3),
    ]

    result = detect_mitigation_block(candles)

    assert result is not None
    assert result["direction"] == Direction.BUY.value
    assert result["source_timestamp"] == candles[4].timestamp.isoformat()
    assert result["displacement_timestamp"] == candles[5].timestamp.isoformat()
    assert result["retest_timestamp"] == candles[6].timestamp.isoformat()
    assert result["mean_threshold"] == pytest.approx(10.225)


def test_pd_arrays_classify_and_align_zones_against_equilibrium() -> None:
    arrays = build_pd_arrays(
        fvg={"direction": "BUY", "low": 10.0, "high": 11.0},
        order_block={"direction": "SELL", "low": 16.0, "high": 18.0},
        breaker_block=None,
        ote={"direction": "BUY", "low": 12.0, "high": 14.0},
        dealing_range={"range_low": 10.0, "range_high": 20.0},
    )

    assert [item["type"] for item in arrays] == ["FVG", "ORDER_BLOCK", "OTE"]
    assert arrays[0]["price_zone"] == "DISCOUNT"
    assert arrays[0]["aligned"] is True
    assert arrays[1]["price_zone"] == "PREMIUM"
    assert arrays[1]["aligned"] is True
    assert arrays[2]["price_zone"] == "DISCOUNT"


def test_advanced_detectors_reject_naive_datetimes() -> None:
    naive = Candle(datetime(2026, 1, 1), 10, 11, 9, 10, 1)

    with pytest.raises(ValueError, match="timezone-aware"):
        detect_turtle_soup([naive] * 4)


def test_backtest_enters_on_next_candle_and_resolves_same_bar_stop_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ict_scanner.ict import backtesting

    candles = [
        candle(0, 10, 10.2, 9.8, 10),
        candle(1, 10, 10.2, 9.8, 10),
        candle(2, 10, 10.2, 9.8, 10),
        candle(3, 10, 10.3, 9.7, 10.1),
        candle(4, 10, 12.2, 8.9, 10.4),
        candle(5, 10.4, 10.5, 10.1, 10.3),
    ]
    target_signal = {
        "direction": "BUY",
        "stop_reference": 9.0,
        "timestamp": candles[3].timestamp.isoformat(),
    }

    monkeypatch.setattr(
        backtesting,
        "detect_turtle_soup",
        lambda history: target_signal if history[-1] is candles[3] else None,
    )

    summary = backtest_turtle_soup(candles)

    assert len(summary.trades) == 1
    assert summary.trades[0].entry_time == candles[4].timestamp.isoformat()
    assert summary.trades[0].entry == candles[4].open
    assert summary.trades[0].result_r == -1.0
    assert (summary.wins, summary.losses, summary.expired) == (0, 1, 0)


def test_backtest_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="reward_to_risk"):
        backtest_turtle_soup([], reward_to_risk=0)
    with pytest.raises(ValueError, match="reward_to_risk"):
        backtest_turtle_soup([], reward_to_risk=float("nan"))
    with pytest.raises(ValueError, match="max_holding_candles"):
        backtest_turtle_soup([], max_holding_candles=0)
