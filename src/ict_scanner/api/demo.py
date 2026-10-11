from contextlib import asynccontextmanager

from fastapi import FastAPI
from ict_scanner.api.dashboard_routes import dashboard_router
from ict_scanner.api.demo_routes import router
from ict_scanner.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="ICT Scanner Dashboard and EUR/USD Demo", lifespan=lifespan)
app.include_router(router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
