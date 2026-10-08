from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from typing import List, Dict, Any
from sqlalchemy.future import select
from ict_scanner.db.database import async_session
from ict_scanner.db.models import PairConfig, DetectedSetup, SystemHealthLog, AlertLog, AIEvaluation
from ict_scanner.config.settings import settings

router = APIRouter()

def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

@router.get("/health")
async def get_health():
    async with async_session() as session:
        result = await session.execute(
            select(SystemHealthLog).order_by(SystemHealthLog.recorded_at.desc()).limit(1)
        )
        log = result.scalars().first()
        status = log.status if log else "UNKNOWN"
        return {"status": status}

@router.get("/pairs", dependencies=[Depends(verify_api_key)])
async def get_pairs():
    async with async_session() as session:
        result = await session.execute(select(PairConfig))
        pairs = result.scalars().all()
        return pairs

@router.post("/pairs/toggle", dependencies=[Depends(verify_api_key)])
async def toggle_pair(data: dict):
    symbol = data.get("symbol")
    async with async_session() as session:
        result = await session.execute(select(PairConfig).where(PairConfig.symbol == symbol))
        pair = result.scalars().first()
        if not pair:
            raise HTTPException(status_code=404, detail="Pair not found")
        pair.is_active = not pair.is_active
        await session.commit()
        return {"status": "success", "is_active": pair.is_active}

@router.get("/setups", dependencies=[Depends(verify_api_key)])
async def get_setups():
    async with async_session() as session:
        # Join setups and ai evaluations
        query = select(DetectedSetup, AIEvaluation).join(
            AIEvaluation, DetectedSetup.id == AIEvaluation.setup_id, isouter=True
        ).order_by(DetectedSetup.created_at.desc()).limit(50)
        
        result = await session.execute(query)
        rows = result.all()
        
        res = []
        for setup, eval in rows:
            res.append({
                "id": setup.id,
                "symbol": setup.symbol,
                "direction": setup.direction,
                "timeframe": setup.timeframe,
                "created_at": setup.created_at,
                "probability_score": eval.probability_score if eval else None,
                "approved": eval.approved_for_alert if eval else False,
            })
        return res

@router.get("/settings", dependencies=[Depends(verify_api_key)])
async def get_settings():
    return {
        "min_probability_threshold": settings.min_probability_threshold,
        "min_rr": settings.min_rr,
        "scan_interval_seconds": settings.scan_interval_seconds
    }

@router.post("/settings", dependencies=[Depends(verify_api_key)])
async def update_settings(data: dict):
    # In a real app we might persist these to DB or .env, but for now we just update in-memory
    if "min_probability_threshold" in data:
        settings.min_probability_threshold = int(data["min_probability_threshold"])
    if "min_rr" in data:
        settings.min_rr = float(data["min_rr"])
    if "scan_interval_seconds" in data:
        settings.scan_interval_seconds = int(data["scan_interval_seconds"])
    return {"status": "success"}

@router.get("/logs", dependencies=[Depends(verify_api_key)])
async def get_logs():
    async with async_session() as session:
        h_result = await session.execute(select(SystemHealthLog).order_by(SystemHealthLog.recorded_at.desc()).limit(10))
        health_logs = h_result.scalars().all()
        
        a_result = await session.execute(select(AlertLog).order_by(AlertLog.dispatched_at.desc()).limit(10))
        alert_logs = a_result.scalars().all()
        
        return {
            "health": health_logs,
            "alerts": alert_logs
        }

@router.post("/scan/manual", dependencies=[Depends(verify_api_key)])
async def manual_scan(request: Request):
    app = request.app
    # The scheduler is stored in app.state
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        # Trigger an asynchronous one-off run without blocking the web request
        import asyncio
        asyncio.create_task(scheduler.run_once())
        return {"status": "scan initiated"}
    return {"status": "error", "detail": "Scheduler not available"}
