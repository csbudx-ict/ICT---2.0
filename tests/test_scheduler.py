import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from db.database import init_db
from db.models import PairConfig, DetectedSetup, AIEvaluation, AlertLog, SystemHealthLog
from db.database import async_session
from sqlalchemy.future import select
from core.scheduler import Scheduler
from core.ict.engine import generate_dedupe_key
from config.settings import settings

async def init_test_db():
    import os
    if os.path.exists("test.db"):
        os.remove("test.db")
        
    settings.database_url = "sqlite+aiosqlite:///test.db"
    from db.database import engine, enable_wal, seed_pairs
    from db.models import Base
    
    # Re-initialize engine
    from sqlalchemy.ext.asyncio import create_async_engine
    engine.sync_engine.dispose()
    
    # Override engine in async_session
    new_engine = create_async_engine("sqlite+aiosqlite:///test.db", echo=False)
    
    import db.database
    db.database.engine = new_engine
    
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    db.database.async_session = async_sessionmaker(new_engine, expire_on_commit=False, class_=AsyncSession)
    
    import core.scheduler
    core.scheduler.async_session = db.database.async_session
    
    # Override local module async_session variable
    global async_session
    async_session = db.database.async_session
    
    async with new_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    # Insert a test pair
    async with async_session() as session:
        session.add(PairConfig(symbol="TEST/USD", asset_class="forex", provider="test", is_active=True))
        await session.commit()
        
    return new_engine

@pytest.mark.asyncio
async def test_scheduler_process_pair():
    engine = await init_test_db()
    settings.openai_api_key = "dummy_key"
    scheduler = Scheduler()
    
    # Mock DataFeed
    dates = [datetime(2023, 1, 1, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=5*i) for i in range(30)]
    
    data = []
    base_price = 1.1000
    for i in range(30):
        open_p = base_price
        close = base_price
        high = base_price + 0.0010
        low = base_price - 0.0010
        if i == 5:
            low = base_price - 0.0030
            high = base_price - 0.0010
        if i == 15:
            low = base_price - 0.0040
            high = base_price + 0.0010
            close = base_price - 0.0020
        if i == 18:
            low = base_price
            high = base_price + 0.0030
            close = base_price + 0.0010
        if i == 20:
            low = base_price - 0.0010
            high = base_price + 0.0015
            close = base_price + 0.0010
        if i == 21:
            low = base_price + 0.0010
            high = base_price + 0.0060
            close = base_price + 0.0050
            open_p = base_price + 0.0010
        if i == 22:
            low = base_price + 0.0040
            high = base_price + 0.0070
            close = base_price + 0.0050
            open_p = base_price + 0.0040
        data.append({'Open': open_p, 'High': high, 'Low': low, 'Close': close})
        
    df = pd.DataFrame(data, index=dates)
    scheduler.data_feed.fetch_candles = AsyncMock(return_value=df)
    
    # Mock AI Evaluator
    scheduler.ai_evaluator.evaluate_setup = AsyncMock(return_value={
        'probability_score': 85,
        'approved': True,
        'market_bias': 'Bullish',
        'thesis': 'Test thesis',
        'invalidation': 'Test invalidation'
    })
    
    # Mock Notifiers
    scheduler.telegram.send_alert = AsyncMock(return_value=True)
    scheduler.email.send_alert = AsyncMock(return_value=True)
    
    async with async_session() as session:
        result = await session.execute(select(PairConfig).where(PairConfig.symbol == "TEST/USD"))
        pair = result.scalars().first()
        
    await scheduler.process_pair(pair)
    
    # Verify DB state
    async with async_session() as session:
        setups = (await session.execute(select(DetectedSetup))).scalars().all()
        assert len(setups) == 1
        assert setups[0].symbol == "TEST/USD"
        
        evals = (await session.execute(select(AIEvaluation))).scalars().all()
        assert len(evals) == 1
        assert evals[0].probability_score == 85
        assert evals[0].approved_for_alert is True
        
        alert_logs = (await session.execute(select(AlertLog))).scalars().all()
        assert len(alert_logs) == 2
        assert alert_logs[0].channel == "TELEGRAM"
        assert alert_logs[0].status == "SENT"
        assert alert_logs[1].channel == "EMAIL"
        assert alert_logs[1].status == "SENT"
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_scheduler_loop_non_blocking():
    engine = await init_test_db()
    settings.openai_api_key = "dummy_key"
    scheduler = Scheduler()
    scheduler.data_feed.fetch_candles = AsyncMock(return_value=pd.DataFrame())
    
    import asyncio
    # Run loop for a short time to verify it doesn't block indefinitely
    settings.scan_interval_seconds = 1
    scheduler.task = asyncio.create_task(scheduler.loop())
    
    await asyncio.sleep(1.5)
    await scheduler.stop()
    
    async with async_session() as session:
        health_logs = (await session.execute(select(SystemHealthLog))).scalars().all()
        assert len(health_logs) >= 1
        assert health_logs[0].component == "Scheduler"
        assert health_logs[0].status == "HEALTHY"
        
    await engine.dispose()
