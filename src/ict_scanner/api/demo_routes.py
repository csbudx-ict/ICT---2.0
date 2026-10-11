import asyncio
import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ict_scanner.config.settings import settings
from ict_scanner.domain.models import Candle
from ict_scanner.ict.engine import analyze_ict_modules
from ict_scanner.orchestrator.data_feed import DataFeedManager, dataframe_to_candles

router = APIRouter()
LIVE_SYMBOLS = ("EUR/USD", "GBP/USD", "XAU/USD")
LIVE_MODULES = (
    "unicorn_setup",
    "silver_bullet_fvg",
    "institutional_order_block",
    "breaker_blocks",
    "ote_fibonacci",
    "premium_discount",
    "box_liquidity",
)
DEFAULT_ENABLED_MODULES = {module: True for module in LIVE_MODULES}


def _validate_module_selection(message: object) -> dict[str, bool]:
    if not isinstance(message, dict) or message.get("type") != "configure":
        raise ValueError("expected a configure message")
    modules = message.get("modules")
    if not isinstance(modules, dict) or set(modules) != set(LIVE_MODULES):
        raise ValueError("configure message must include every ICT module toggle")
    if any(type(enabled) is not bool for enabled in modules.values()):
        raise ValueError("module toggles must be booleans")
    return {module: modules[module] for module in LIVE_MODULES}


def _build_symbol_update(
    symbol: str,
    candles: Sequence[Candle],
    enabled_modules: Mapping[str, bool],
) -> dict[str, object]:
    if not candles:
        raise ValueError("at least one closed candle is required")

    analysis = analyze_ict_modules(candles)
    module_snapshots = {
        module: {
            "enabled": enabled_modules[module],
            "signal": (
                analysis[module]
                if enabled_modules[module] and isinstance(analysis[module], dict)
                else None
            ),
        }
        for module in LIVE_MODULES
    }
    latest = candles[-1]
    return {
        "symbol": symbol,
        "status": "live",
        "timeframe": "1min",
        "price": latest.close,
        "candle": {
            "timestamp": latest.timestamp.isoformat(),
            "open": latest.open,
            "high": latest.high,
            "low": latest.low,
            "close": latest.close,
        },
        "modules": module_snapshots,
    }


async def _read_market_symbol(
    data_feed: DataFeedManager,
    symbol: str,
    enabled_modules: Mapping[str, bool],
    cached_candles: Sequence[Candle] | None = None,
) -> tuple[dict[str, object], list[Candle] | None]:
    if not settings.twelve_data_api_key:
        return (
            {
                "symbol": symbol,
                "status": "unavailable",
                "error": "TWELVE_DATA_API_KEY is not configured in the backend environment.",
            },
            None,
        )

    try:
        if cached_candles is None:
            frame = await data_feed.fetch_twelvedata_candles(
                symbol,
                timeframe="1min",
                limit=120,
            )
            if frame is None or frame.empty:
                return (
                    {
                        "symbol": symbol,
                        "status": "unavailable",
                        "error": "Twelve Data returned no closed 1-minute candles for this symbol.",
                    },
                    None,
                )
            candles = dataframe_to_candles(frame)
        else:
            candles = list(cached_candles)
        return _build_symbol_update(symbol, candles, enabled_modules), candles
    except (ValueError, KeyError, TypeError) as error:
        return (
            {
                "symbol": symbol,
                "status": "unavailable",
                "error": f"Closed candle analysis failed ({type(error).__name__}).",
            },
            None,
        )


@router.websocket("/ws/live-market")
@router.websocket("/ws/demo/eurusd")
async def stream_live_market(websocket: WebSocket) -> None:
    """Stream live Twelve Data candles over the dashboard WebSocket."""
    await websocket.accept()
    data_feed = DataFeedManager()
    enabled_modules = DEFAULT_ENABLED_MODULES.copy()
    configuration_changed = asyncio.Event()
    configuration_changed.set()
    candle_cache: dict[str, list[Candle] | None] = {}
    poll_provider = True

    try:
        try:
            initial_message = await asyncio.wait_for(websocket.receive_json(), timeout=5)
            enabled_modules = _validate_module_selection(initial_message)
        except TimeoutError:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Send all seven module toggles to start live scanning.",
                }
            )
            await websocket.close(code=1008)
            return
        except (ValueError, json.JSONDecodeError) as error:
            await websocket.send_json({"type": "error", "message": str(error)})
            await websocket.close(code=1008)
            return

        async def receive_configuration() -> None:
            nonlocal enabled_modules
            while True:
                try:
                    message = await websocket.receive_json()
                except WebSocketDisconnect:
                    return
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {"type": "error", "message": "configuration must be valid JSON"}
                    )
                    continue

                try:
                    enabled_modules = _validate_module_selection(message)
                except ValueError as error:
                    await websocket.send_json({"type": "error", "message": str(error)})
                    continue
                configuration_changed.set()

        configuration_task = asyncio.create_task(receive_configuration())
        try:
            while True:
                configuration_changed.clear()
                active_selection = enabled_modules.copy()
                symbols_and_candles = await asyncio.gather(
                    *(
                        _read_market_symbol(
                            data_feed,
                            symbol,
                            active_selection,
                            cached_candles=None if poll_provider else candle_cache.get(symbol),
                        )
                        for symbol in LIVE_SYMBOLS
                    )
                )
                symbols = []
                for symbol, (update, candles) in zip(LIVE_SYMBOLS, symbols_and_candles):
                    symbols.append(update)
                    candle_cache[symbol] = candles
                await websocket.send_json(
                    {
                        "type": "market_update",
                        "provider": "Twelve Data",
                        "generated_at": datetime.now(UTC).isoformat(),
                        "poll_interval_seconds": settings.twelve_data_poll_interval_seconds,
                        "symbols": symbols,
                    }
                )
                try:
                    await asyncio.wait_for(
                        configuration_changed.wait(),
                        timeout=max(10, settings.twelve_data_poll_interval_seconds),
                    )
                    poll_provider = False
                except TimeoutError:
                    poll_provider = True
        except WebSocketDisconnect:
            pass
        finally:
            configuration_task.cancel()
            with suppress(asyncio.CancelledError):
                await configuration_task
    except WebSocketDisconnect:
        pass
    finally:
        await data_feed.close()
