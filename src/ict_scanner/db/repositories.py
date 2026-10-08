from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ict_scanner.db.models import PairConfig, DetectedSetup


class PairRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_active_pairs(self) -> Sequence[PairConfig]:
        stmt = select(PairConfig).where(PairConfig.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalars().all()

class SetupRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dedupe_key(self, dedupe_key: str) -> DetectedSetup | None:
        stmt = select(DetectedSetup).where(DetectedSetup.dedupe_key == dedupe_key)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
        
    async def save(self, setup: DetectedSetup) -> DetectedSetup:
        self.session.add(setup)
        await self.session.flush() # App will commit
        return setup
