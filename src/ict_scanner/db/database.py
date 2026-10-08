import asyncio
import json
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from ict_scanner.db.models import Base, PairConfig
from ict_scanner.config.settings import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def enable_wal():
    # Only applies to SQLite, check engine URL
    if "sqlite" in settings.database_url:
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA busy_timeout=5000;"))

async def seed_pairs():
    async with async_session() as session:
        # Check if pairs exist
        from sqlalchemy import select
        result = await session.execute(select(PairConfig))
        if result.scalars().first():
            return
            
        # Seed from config/pairs.json
        pairs_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'pairs.json')
        if os.path.exists(pairs_file):
            with open(pairs_file, 'r') as f:
                pairs_data = json.load(f)
                
            for p in pairs_data:
                pair = PairConfig(
                    symbol=p["symbol"],
                    asset_class=p["asset_class"],
                    is_active=p.get("is_active", True),
                    timeframes=p.get("timeframes", "1D,4H,15M,5M"),
                    provider=p.get("provider", "")
                )
                session.add(pair)
            
            await session.commit()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await enable_wal()
    await seed_pairs()

if __name__ == "__main__":
    asyncio.run(init_db())
