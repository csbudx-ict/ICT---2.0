from dataclasses import dataclass
from datetime import datetime

from .enums import Direction, Session, SetupStatus, Timeframe


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass(frozen=True)
class Swing:
    type: str  # 'HIGH' or 'LOW'
    price: float
    timestamp: datetime

@dataclass(frozen=True)
class LiquidityPool:
    type: str  # 'BSL' or 'SSL'
    price: float
    source: str  # 'SWING', 'PDH', 'PDL', 'EQH', 'EQL', 'ASIAN_HIGH', 'ASIAN_LOW'
    timestamp: datetime

@dataclass(frozen=True)
class Sweep:
    pool: LiquidityPool
    wick_extreme: float
    sweep_candle: Candle

@dataclass(frozen=True)
class FVG:
    direction: Direction
    low: float
    high: float
    creation_time: datetime
    mitigated: bool = False

@dataclass(frozen=True)
class OrderBlock:
    direction: Direction
    low: float
    high: float
    candle: Candle

@dataclass(frozen=True)
class Setup:
    symbol: str
    direction: Direction
    session_name: Session
    entry_tf: Timeframe
    status: SetupStatus
    sweep_level: float
    sweep_type: str
    mss_level: float
    displacement_atr: float
    fvg_low: float
    fvg_high: float
    ob_low: float | None
    ob_high: float | None
    ote_low: float
    ote_high: float
    range_low: float
    range_high: float
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    rr1: float
    rr2: float
    rule_score: float
    dedupe_key: str
    created_at: datetime
    expires_at: datetime
    
@dataclass
class TradePlan:
    setup: Setup
    risk_percent: float
    account_balance: float
