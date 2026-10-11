import os
from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fastapi import FastAPI
from ict_scanner.api.dashboard_routes import dashboard_router
from ict_scanner.api.demo_routes import router as market_router
from ict_scanner.api.routes import router
from ict_scanner.db.database import init_db
from ict_scanner.orchestrator.scheduler import Scheduler

scheduler = Scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await scheduler.start()
    app.state.scheduler = scheduler
    yield
    await scheduler.stop()


app = FastAPI(lifespan=lifespan, title="ICT Scanner Admin API")

app.include_router(router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(market_router, prefix="/api")

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount charts directory
charts_dir = os.path.join(os.getcwd(), "data", "charts")
os.makedirs(charts_dir, exist_ok=True)
app.mount("/charts", StaticFiles(directory=charts_dir), name="charts")


@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Admin panel not found. Please create index.html in api/static."}
