from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, 
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

class PairConfig(Base):
    __tablename__ = "pairs_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(30), unique=True, nullable=False)
    asset_class = Column(String(15), nullable=False)
    is_active = Column(Boolean, default=True)
    timeframes = Column(String(60), default="1D,4H,15M,5M")
    provider = Column(String(30))
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class DetectedSetup(Base):
    __tablename__ = "detected_setups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(30), nullable=False)
    session_name = Column(String(30), nullable=False)
    timeframe = Column(String(10), nullable=False)
    direction = Column(String(10), nullable=False)
    sweep_level = Column(Float, nullable=False)
    displacement_atr = Column(Float, nullable=False)
    fvg_high = Column(Float, nullable=False)
    fvg_low = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    rr_ratio = Column(Float, nullable=False)
    dedupe_key = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)

class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setup_id = Column(Integer, ForeignKey("detected_setups.id", ondelete="CASCADE"), nullable=False)
    probability_score = Column(Integer, nullable=False)
    market_bias = Column(String(20), nullable=False)
    narrative_thesis = Column(Text, nullable=False)
    invalidation_rule = Column(Text, nullable=False)
    approved_for_alert = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setup_id = Column(Integer, ForeignKey("detected_setups.id"), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    response_payload = Column(Text)
    dispatched_at = Column(DateTime, default=utcnow)

class SystemHealthLog(Base):
    __tablename__ = "system_health_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    message = Column(Text)
    recorded_at = Column(DateTime, default=utcnow)
