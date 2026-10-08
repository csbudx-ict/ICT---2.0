

def get_fib_levels(low: float, high: float) -> dict[float, float]:
    diff = high - low
    levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1.0, -0.27, -0.62, -1.0]
    return {lvl: high - (diff * lvl) for lvl in levels} # Anchor top to bottom

def get_ote_zone(low: float, high: float, direction: str) -> tuple[float, float]:
    """OTE zone is 0.618 - 0.786 of the dealing range."""
    diff = high - low
    if direction == "BUY":
        # Anchor is high, pull to low. Retracement from low upwards.
        return low + (diff * 0.618), low + (diff * 0.786)
    else:
        return high - (diff * 0.786), high - (diff * 0.618)

def is_in_ote(price: float, ote_low: float, ote_high: float) -> bool:
    return ote_low <= price <= ote_high
