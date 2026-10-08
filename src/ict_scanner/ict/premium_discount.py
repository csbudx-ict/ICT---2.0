
from ict_scanner.domain.enums import Direction


def get_dealing_range(low: float, high: float) -> tuple[float, float, float]:
    """Returns range_low, range_high, equilibrium."""
    return low, high, (low + high) / 2.0

def is_in_discount(price: float, eq: float) -> bool:
    """Price is below equilibrium."""
    return price < eq

def is_in_premium(price: float, eq: float) -> bool:
    """Price is above equilibrium."""
    return price > eq

def validate_pd_alignment(entry: float, eq: float, direction: Direction) -> bool:
    """BUY must be in Discount, SELL must be in Premium."""
    if direction == Direction.BUY:
        return is_in_discount(entry, eq)
    else:
        return is_in_premium(entry, eq)
