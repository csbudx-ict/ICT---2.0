from datetime import UTC, datetime

from ict_scanner.data.candle_store import CandleStore
from ict_scanner.domain.enums import Timeframe
from ict_scanner.domain.models import Candle


def test_candle_store() -> None:
    store = CandleStore(max_len=5)
    dt = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c1 = Candle(timestamp=dt, open=1.0, high=2.0, low=0.5, close=1.5, volume=100)
    
    store.add_candle("BTC/USDT", Timeframe.M5, c1)
    candles = store.get_candles("BTC/USDT", Timeframe.M5)
    
    assert len(candles) == 1
    assert candles[0] == c1
    
    assert len(store.get_candles("ETH/USDT", Timeframe.M5)) == 0
