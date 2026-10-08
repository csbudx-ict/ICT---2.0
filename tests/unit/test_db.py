
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ict_scanner.db.models import Base, PairConfig
from ict_scanner.db.repositories import PairRepository


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_pair_repository(db_session: AsyncSession) -> None:
    # Seed active pair
    pair = PairConfig(symbol="EUR/USD", asset_class="forex", provider="twelvedata", is_active=True)
    db_session.add(pair)
    
    # Seed inactive pair
    pair2 = PairConfig(symbol="BTC/USDT", asset_class="crypto", provider="ccxt", is_active=False)
    db_session.add(pair2)
    
    await db_session.commit()
    
    repo = PairRepository(db_session)
    active_pairs = await repo.get_active_pairs()
    
    assert len(active_pairs) == 1
    assert active_pairs[0].symbol == "EUR/USD"
