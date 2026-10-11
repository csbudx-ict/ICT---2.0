from datetime import UTC, datetime

from ict_scanner.domain.enums import Session


def get_active_killzone(dt: datetime) -> Session:
    """Check UTC time for ICT Killzones."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("killzone timestamp must be timezone-aware")
    dt = dt.astimezone(UTC)
    hour = dt.hour

    if 0 <= hour < 6:
        return Session.ASIAN
    elif 7 <= hour < 10:
        return Session.LONDON
    elif 12 <= hour < 15:
        return Session.NEW_YORK_AM
    elif 15 <= hour < 17:
        return Session.LONDON_CLOSE

    return Session.OUTSIDE


def is_valid_killzone(session: Session) -> bool:
    """Only London and NY AM are valid for our entries."""
    return session in [Session.LONDON, Session.NEW_YORK_AM]
