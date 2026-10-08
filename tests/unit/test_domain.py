from datetime import UTC, datetime

from ict_scanner.domain.enums import AssetClass, Direction, Timeframe
from ict_scanner.domain.models import Candle


def test_candle_creation() -> None:
    dt = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c = Candle(timestamp=dt, open=1.0, high=2.0, low=0.5, close=1.5, volume=100)
    assert c.open == 1.0
    assert c.high == 2.0
    assert c.low == 0.5
    assert c.close == 1.5

def test_enums() -> None:
    assert Direction.BUY.value == "BUY"
    assert Timeframe.M5.value == "5m"
    assert AssetClass.CRYPTO.value == "crypto"
