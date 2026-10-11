from datetime import UTC, datetime, timedelta

import pytest

from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle
from ict_scanner.orchestrator.demo_feed import build_demo_candle, detect_closed_candle_fvg


def build_candles(count: int) -> list[Candle]:
    candles = []
    previous_close = 1.0845
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(count):
        candle = build_demo_candle(index, previous_close, start + timedelta(seconds=index))
        candles.append(candle)
        previous_close = candle.close
    return candles


def test_detects_fvg_only_after_three_closed_candles() -> None:
    candles = build_candles(3)

    assert detect_closed_candle_fvg(candles[:2]) is None
    fvg = detect_closed_candle_fvg(candles)

    assert fvg is not None
    assert fvg.direction is Direction.BUY
    assert fvg.low < fvg.high
    assert fvg.creation_time == candles[-1].timestamp


def test_alternates_to_a_bearish_fvg() -> None:
    candles = build_candles(15)

    fvg = detect_closed_candle_fvg(candles[-3:])

    assert fvg is not None
    assert fvg.direction is Direction.SELL
    assert fvg.low < fvg.high


@pytest.mark.parametrize(
    ("index", "previous_close", "timestamp"),
    [
        (-1, 1.0, datetime(2026, 1, 1, tzinfo=UTC)),
        (0, float("nan"), datetime(2026, 1, 1, tzinfo=UTC)),
        (0, 1.0, datetime(2026, 1, 1)),
    ],
)
def test_rejects_invalid_candle_inputs(
    index: int, previous_close: float, timestamp: datetime
) -> None:
    with pytest.raises(ValueError):
        build_demo_candle(index, previous_close, timestamp)
