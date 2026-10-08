
from ict_scanner.domain.enums import Direction
from ict_scanner.domain.models import FVG, OrderBlock


def calculate_levels(
    direction: Direction, 
    sweep_extreme: float, 
    fvg: FVG, 
    ob: OrderBlock | None, 
    atr_buffer: float,
    fib_levels: dict[float, float]
) -> tuple[float, float, float, float]:
    """Calculate Entry, Stop Loss, TP1, and TP2."""
    
    # Entry is FVG consequent encroachment (midpoint) by default
    entry = (fvg.low + fvg.high) / 2.0
    
    # SL is sweep extreme + buffer
    if direction == Direction.BUY:
        sl = sweep_extreme - atr_buffer
        tp1 = fib_levels[0.0]  # The high of the dealing range
        tp2 = fib_levels[-0.27] # Fib extension
    else:
        sl = sweep_extreme + atr_buffer
        tp1 = fib_levels[0.0]  # The low of the dealing range
        tp2 = fib_levels[-0.27]
        
    return entry, sl, tp1, tp2

def calculate_rr(entry: float, sl: float, tp: float) -> float:
    risk = abs(entry - sl)
    if risk == 0:
        return 0.0
    reward = abs(tp - entry)
    return reward / risk
