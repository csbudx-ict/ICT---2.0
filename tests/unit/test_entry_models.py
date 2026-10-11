from datetime import UTC, datetime, timedelta

import pytest

import pandas as pd
from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle
from ict_scanner.ict.fractals import identify_swings
from ict_scanner.ict.institutional_order_block import detect_institutional_order_block
from ict_scanner.ict.silver_bullet import detect_silver_bullet_fvg
from ict_scanner.ict.unicorn import detect_unicorn_setup


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


def breaker_mss_fvg_candles() -> list[Candle]:
    candles = [candle(index, 100.4, 100.6, 100.2, 100.4) for index in range(21)]
    candles[3] = candle(3, 100.0, 101.0, 99.8, 100.8)
    candles[6] = candle(6, 100.7, 101.3, 100.6, 101.1)
    candles[14] = candle(14, 100.4, 100.9, 100.1, 100.5)
    candles[18] = candle(18, 100.8, 101.0, 100.4, 100.6)
    candles[19] = candle(19, 100.8, 102.9, 100.7, 102.8)
    candles[20] = candle(20, 101.7, 102.0, 101.01, 101.8)
    return candles


def mirrored(candles: list[Candle]) -> list[Candle]:
    return [
        Candle(
            timestamp=item.timestamp,
            open=200 - item.open,
            high=200 - item.low,
            low=200 - item.high,
            close=200 - item.close,
            volume=item.volume,
        )
        for item in candles
    ]


def swing_frame(candles: list[Candle]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "Open": [item.open for item in candles],
            "High": [item.high for item in candles],
            "Low": [item.low for item in candles],
            "Close": [item.close for item in candles],
        }
    )
    return identify_swings(frame)


@pytest.mark.parametrize(
    ("candles", "direction", "low", "high", "proximal", "distal"),
    [
        (
            [
                candle(0, 10, 10.3, 9.9, 10),
                candle(1, 10, 10.8, 10, 10.7),
                candle(2, 10.7, 10.9, 10.4, 10.6),
            ],
            Direction.BUY,
            10.3,
            10.4,
            10.4,
            10.3,
        ),
        (
            [
                candle(0, 10, 10.1, 10, 10),
                candle(1, 10, 10, 9.2, 9.3),
                candle(2, 9.5, 9.6, 9.4, 9.5),
            ],
            Direction.SELL,
            9.6,
            10,
            9.6,
            10,
        ),
    ],
)
def test_silver_bullet_fvg_maps_directional_retracement_boundaries(
    candles: list[Candle],
    direction: Direction,
    low: float,
    high: float,
    proximal: float,
    distal: float,
) -> None:
    signal = detect_silver_bullet_fvg(candles)

    assert signal is not None
    assert signal["direction"] == direction.value
    assert signal["low"] == low
    assert signal["high"] == high
    assert signal["midpoint"] == pytest.approx((low + high) / 2)
    assert signal["retracement_entry"] == signal["midpoint"]
    assert signal["proximal_boundary"] == proximal
    assert signal["distal_boundary"] == distal


def test_silver_bullet_fvg_requires_a_gap_between_candles_one_and_three() -> None:
    candles = [
        candle(0, 10, 10.3, 9.8, 10),
        candle(1, 10, 10.2, 9.9, 10.1),
        candle(2, 10.1, 10.3, 9.8, 10),
    ]

    assert detect_silver_bullet_fvg(candles) is None
    assert detect_silver_bullet_fvg(candles[:2]) is None


def test_silver_bullet_fvg_rejects_naive_candle_timestamps() -> None:
    candles = [
        Candle(datetime.fromisoformat("2026-01-01"), 10, 10.3, 9.9, 10, 1),
        candle(1, 10, 10.8, 10, 10.7),
        candle(2, 10.7, 10.9, 10.4, 10.6),
    ]

    with pytest.raises(ValueError, match="timezone-aware"):
        detect_silver_bullet_fvg(candles)


def test_unicorn_requires_mss_fvg_touching_a_previously_formed_breaker() -> None:
    candles = breaker_mss_fvg_candles()
    frame = swing_frame(candles)

    signal = detect_unicorn_setup(candles, frame, displacement_atr_multiplier=1.5)

    assert signal is not None
    assert signal["direction"] == Direction.BUY.value
    assert signal["breaker_formed_at"] == candles[6].timestamp.isoformat()
    assert signal["mss_timestamp"] == candles[19].timestamp.isoformat()
    assert signal["fvg_timestamp"] == candles[20].timestamp.isoformat()
    assert signal["fvg_low"] == signal["breaker_high"]


def test_unicorn_detects_the_mirrored_bearish_setup() -> None:
    candles = mirrored(breaker_mss_fvg_candles())
    signal = detect_unicorn_setup(candles, swing_frame(candles), 1.5)

    assert signal is not None
    assert signal["direction"] == Direction.SELL.value
    assert signal["fvg_high"] == signal["breaker_low"]


def test_unicorn_rejects_an_fvg_separated_from_the_breaker() -> None:
    candles = breaker_mss_fvg_candles()
    candles[18] = candle(18, 101.1, 101.3, 100.8, 100.9)
    candles[20] = candle(20, 101.7, 102.0, 101.4, 101.8)

    assert detect_unicorn_setup(candles, swing_frame(candles), 1.5) is None


def test_institutional_ob_requires_the_impulse_mss_and_marks_mean_threshold() -> None:
    candles = breaker_mss_fvg_candles()[:20]
    signal = detect_institutional_order_block(candles, swing_frame(candles), 1.5)

    assert signal is not None
    assert signal["direction"] == Direction.BUY.value
    assert signal["order_block_timestamp"] == candles[18].timestamp.isoformat()
    assert signal["mean_threshold"] == pytest.approx((candles[18].low + candles[18].high) / 2)
    assert signal["mitigation_entry"] == signal["mean_threshold"]


def test_institutional_ob_detects_the_mirrored_bearish_impulse() -> None:
    candles = mirrored(breaker_mss_fvg_candles()[:20])
    signal = detect_institutional_order_block(candles, swing_frame(candles), 1.5)

    assert signal is not None
    assert signal["direction"] == Direction.SELL.value
    assert signal["order_block_timestamp"] == candles[18].timestamp.isoformat()


def test_institutional_ob_rejects_an_impulse_without_an_mss() -> None:
    candles = breaker_mss_fvg_candles()[:20]
    candles[-1] = candle(19, 100.5, 100.7, 100.3, 100.6)

    assert detect_institutional_order_block(candles, swing_frame(candles), 1.5) is None
