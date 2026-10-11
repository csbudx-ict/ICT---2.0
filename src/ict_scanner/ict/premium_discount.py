from math import isfinite

from ict_scanner.domain.enums import Direction


def get_dealing_range(low: float, high: float) -> tuple[float, float, float]:
    """Returns range_low, range_high, equilibrium."""
    if not isfinite(low) or not isfinite(high) or high < low:
        raise ValueError("range prices must be finite and high must not be below low")
    return low, high, (low + high) / 2.0


def is_in_discount(price: float, eq: float) -> bool:
    """Price is below equilibrium."""
    return isfinite(price) and isfinite(eq) and price < eq


def is_in_premium(price: float, eq: float) -> bool:
    """Price is above equilibrium."""
    return isfinite(price) and isfinite(eq) and price > eq


def get_price_zone(price: float, low: float, high: float) -> str:
    """Return DISCOUNT, EQUILIBRIUM, or PREMIUM for a price in a dealing range."""
    _, _, equilibrium = get_dealing_range(low, high)
    if not isfinite(price):
        raise ValueError("price must be finite")
    if price < equilibrium:
        return "DISCOUNT"
    if price > equilibrium:
        return "PREMIUM"
    return "EQUILIBRIUM"


def validate_pd_alignment(entry: float, eq: float, direction: Direction) -> bool:
    """BUY must be in Discount, SELL must be in Premium."""
    if direction == Direction.BUY:
        return is_in_discount(entry, eq)
    if direction == Direction.SELL:
        return is_in_premium(entry, eq)
    return False
