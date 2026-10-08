from datetime import UTC, datetime, timedelta

from ict_scanner.domain.enums import Timeframe
from ict_scanner.domain.models import Candle
from ict_scanner.ict.engine import scan_for_setups


def test_engine_no_candles() -> None:
    assert scan_for_setups("BTC/USDT", [], Timeframe.M5) == []

def test_engine_not_enough_candles() -> None:
    candles = [
        Candle(timestamp=datetime.now(UTC) - timedelta(minutes=i*5), open=1, high=2, low=0, close=1.5, volume=100)
        for i in range(10)
    ]
    assert scan_for_setups("BTC/USDT", candles, Timeframe.M5) == []
