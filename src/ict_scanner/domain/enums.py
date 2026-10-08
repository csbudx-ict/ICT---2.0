from enum import Enum


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"

class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class AssetClass(str, Enum):
    FOREX = "forex"
    CRYPTO = "crypto"
    INDEX = "index"

class Session(str, Enum):
    ASIAN = "Asian"
    LONDON = "London"
    NEW_YORK_AM = "New York AM"
    LONDON_CLOSE = "London Close"
    OUTSIDE = "Outside"

class SetupStatus(str, Enum):
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"
    TP1_HIT = "TP1_HIT"
    TP2_HIT = "TP2_HIT"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
