
from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import Candle, OrderBlock


def find_order_block(candles: list[Candle], direction: Direction, displacement_time: float) -> OrderBlock | None:
    """Find the last opposite-colored candle before the displacement leg."""
    if not candles:
        return None
        
    for i in range(len(candles)-1, -1, -1):
        if candles[i].timestamp.timestamp() >= displacement_time:
            continue
            
        c = candles[i]
        if direction == Direction.BUY: # Look for last bearish candle
            if c.close < c.open:
                return OrderBlock(direction=direction, low=c.low, high=c.high, candle=c)
        else: # Look for last bullish candle
            if c.close > c.open:
                return OrderBlock(direction=direction, low=c.low, high=c.high, candle=c)
                
    return None
