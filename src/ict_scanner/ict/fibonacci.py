from math import isfinite

from ict_scanner.domain.enums import Direction

OTE_LOW = 0.618
OTE_SWEET_SPOT = 0.705
OTE_HIGH = 0.79
FIBONACCI_LEVELS = (0.0, 1.0, OTE_LOW, OTE_SWEET_SPOT, OTE_HIGH, -1.0, -0.62, -0.27, 0.5)


def _direction(value: Direction | str) -> Direction:
    try:
        direction = value if isinstance(value, Direction) else Direction(value.upper())
    except ValueError as exc:
        raise ValueError("direction must be BUY or SELL") from exc
    if direction is Direction.NEUTRAL:
        raise ValueError("direction must be BUY or SELL")
    return direction


def _validate_range(low: float, high: float) -> None:
    if not isfinite(low) or not isfinite(high) or high <= low:
        raise ValueError("range must have finite prices with high greater than low")


def get_fib_levels(
    low: float,
    high: float,
    direction: Direction | str = Direction.BUY,
) -> dict[float, float]:
    """Return retracement and extension prices for the chosen impulse direction."""
    _validate_range(low, high)
    selected_direction = _direction(direction)
    if selected_direction is Direction.BUY:
        return {ratio: high - ((high - low) * ratio) for ratio in FIBONACCI_LEVELS}
    return {ratio: low + ((high - low) * ratio) for ratio in FIBONACCI_LEVELS}


def get_ote_zone(
    low: float,
    high: float,
    direction: Direction | str,
) -> tuple[float, float]:
    """Return the ordered 0.618–0.790 retracement prices for a bullish or bearish leg."""
    levels = get_fib_levels(low, high, direction)
    return min(levels[OTE_LOW], levels[OTE_HIGH]), max(levels[OTE_LOW], levels[OTE_HIGH])


def get_ote_sweet_spot(
    low: float,
    high: float,
    direction: Direction | str,
) -> float:
    """Return the 0.705 OTE price."""
    return get_fib_levels(low, high, direction)[OTE_SWEET_SPOT]


def is_in_ote(price: float, ote_low: float, ote_high: float) -> bool:
    if not all(isfinite(value) for value in (price, ote_low, ote_high)):
        return False
    return ote_low <= price <= ote_high
