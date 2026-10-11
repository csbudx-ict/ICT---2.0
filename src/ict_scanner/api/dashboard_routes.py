import asyncio
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from telegram.error import TelegramError

import pandas as pd
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ict_scanner.config.settings import settings
from ict_scanner.db.database import async_session
from ict_scanner.db.models import PairConfig
from ict_scanner.ict.engine import ICT_ENTRY_MODULES, ICT_MODULES, analyze_ict_modules
from ict_scanner.notifications.telegram_bot import TelegramNotifier
from ict_scanner.orchestrator.data_feed import DataFeedManager, dataframe_to_candles

dashboard_router = APIRouter()
DASHBOARD_MODULES = (*ICT_MODULES, "master_sniper", *ICT_ENTRY_MODULES)
DEFAULT_MODULE_SELECTION = {module: True for module in DASHBOARD_MODULES}
ENTRY_MODULES = (*ICT_MODULES, "master_sniper", *ICT_ENTRY_MODULES)
ENTRY_PRIORITY = {
    "master_sniper": 7,
    "unicorn_setup": 6,
    "institutional_order_block": 5,
    "silver_bullet_fvg": 4,
    "breaker_blocks": 3,
    "order_blocks": 2,
    "fvg": 1,
}
logger = structlog.get_logger(__name__)


def collect_detected_entries(pairs: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for pair in pairs:
        if pair.get("status") != "CONNECTED":
            continue
        symbol = pair.get("symbol")
        modules = pair.get("modules")
        if not isinstance(symbol, str) or not isinstance(modules, dict):
            continue

        for module in ENTRY_MODULES:
            snapshot = modules.get(module)
            if not isinstance(snapshot, dict) or snapshot.get("enabled") is not True:
                continue
            signal = snapshot.get("signal")
            if not isinstance(signal, dict):
                continue
            if module == "master_sniper" and signal.get("ready") is not True:
                continue
            direction = signal.get("direction")
            timestamp = next(
                (
                    signal.get(key)
                    for key in ("timestamp", "mss_timestamp", "impulse_timestamp", "fvg_timestamp")
                    if isinstance(signal.get(key), str)
                ),
                pair.get("timestamp"),
            )
            if direction not in ("BUY", "SELL") or not isinstance(timestamp, str):
                continue

            raw_score = signal.get("score", signal.get("displacement_atr", 0))
            signal_score = float(raw_score) if isinstance(raw_score, (int, float)) else 0.0
            identity = hashlib.sha256(f"{symbol}|{module}|{timestamp}".encode()).hexdigest()[:20]
            entry: dict[str, object] = {
                "id": identity,
                "symbol": symbol,
                "module": module,
                "module_label": module.replace("_", " ").title(),
                "direction": direction,
                "timestamp": timestamp,
                "entry": next(
                    (
                        signal[key]
                        for key in ("retracement_entry", "mitigation_entry", "fvg_midpoint")
                        if isinstance(signal.get(key), (int, float))
                    ),
                    None,
                ),
                "low": signal.get("low", signal.get("fvg_low")),
                "high": signal.get("high", signal.get("fvg_high")),
                "mean_threshold": signal.get("mean_threshold"),
                "displacement_atr": signal.get("displacement_atr"),
                "rank": ENTRY_PRIORITY.get(module, 0),
                "rank_score": signal_score,
                "provider": pair.get("provider", ""),
            }
            entries.append(entry)

    return sorted(
        entries,
        key=lambda entry: (
            entry["rank"] if isinstance(entry["rank"], int) else 0,
            entry["rank_score"] if isinstance(entry["rank_score"], float) else 0.0,
            str(entry["timestamp"]),
            str(entry["symbol"]),
        ),
        reverse=True,
    )


def validate_telegram_dispatch(message: object) -> tuple[str, list[str]]:
    if not isinstance(message, dict) or message.get("type") != "telegram_dispatch":
        raise ValueError("Expected a Telegram dispatch message.")
    mode = message.get("mode")
    if mode == "all":
        return mode, []
    entry_ids = message.get("entry_ids")
    if mode != "selected" or not isinstance(entry_ids, list) or not entry_ids:
        raise ValueError("Select one or more entry IDs, or use mode 'all'.")
    if any(not isinstance(entry_id, str) or len(entry_id) != 20 for entry_id in entry_ids):
        raise ValueError("Selected entry IDs are invalid.")
    if len(entry_ids) > 2:
        raise ValueError("A maximum of two selected setups can be sent.")
    if len(set(entry_ids)) != len(entry_ids):
        raise ValueError("Selected entry IDs must be unique.")
    return mode, entry_ids


def format_detected_entry_alert(entry: Mapping[str, object]) -> str:
    def escape(value: object) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def price(value: object) -> str:
        return f"{value:.5f}" if isinstance(value, (int, float)) else "n/a"

    return "\n".join(
        (
            f"🚨 <b>ICT ENTRY: {escape(entry['symbol'])}</b>",
            f"Model: {escape(entry['module_label'])}",
            f"Direction: <b>{escape(entry['direction'])}</b>",
            f"Entry: {price(entry.get('entry'))}",
            f"Zone: {price(entry.get('low'))} – {price(entry.get('high'))}",
            f"Mean threshold: {price(entry.get('mean_threshold'))}",
            f"Displacement: {price(entry.get('displacement_atr'))} ATR",
            f"Closed-candle time: {escape(entry['timestamp'])}",
            f"Provider: {escape(entry.get('provider', ''))}",
            "Informational setup signal; validate risk before trading.",
        )
    )


def validate_module_selection(message: object) -> dict[str, bool]:
    if not isinstance(message, dict) or message.get("type") != "configure":
        raise ValueError("Expected a configure message containing all ICT module toggles.")
    modules = message.get("modules")
    if not isinstance(modules, dict) or set(modules) != set(DASHBOARD_MODULES):
        raise ValueError("Configure messages must include all ICT module toggles.")
    if any(type(enabled) is not bool for enabled in modules.values()):
        raise ValueError("ICT module selections must be booleans.")
    return {module: modules[module] for module in DASHBOARD_MODULES}


def build_pair_snapshot(
    symbol: str,
    provider: str,
    candles_frame: pd.DataFrame,
    selection: Mapping[str, bool],
) -> dict[str, object]:
    candles = dataframe_to_candles(candles_frame)
    analysis = analyze_ict_modules(candles)
    modules = {
        module: {
            "enabled": selection[module],
            "signal": (
                analysis[module]
                if selection[module] and isinstance(analysis[module], dict)
                else None
            ),
        }
        for module in DASHBOARD_MODULES
    }
    if modules["master_sniper"]["enabled"]:
        master_signal = analysis["master_sniper"]
        if isinstance(master_signal, dict):
            missing = [module for module in ICT_MODULES if not selection[module]]
            modules["master_sniper"]["signal"] = {
                **master_signal,
                "ready": master_signal.get("ready") is True and not missing,
                "disabled_dependencies": missing,
            }

    latest = candles[-1]
    return {
        "symbol": symbol,
        "provider": provider,
        "status": "CONNECTED",
        "timestamp": latest.timestamp.isoformat(),
        "candle": {
            "open": latest.open,
            "high": latest.high,
            "low": latest.low,
            "close": latest.close,
        },
        "modules": modules,
        "advanced_ict": analysis.get("advanced_ict"),
    }


async def _configured_pairs() -> list[PairConfig]:
    async with async_session() as session:
        result = await session.execute(
            select(PairConfig).where(PairConfig.is_active.is_(True)).order_by(PairConfig.symbol)
        )
        return list(result.scalars().all())


async def _pair_update(
    feed: DataFeedManager,
    pair: PairConfig,
    selection: Mapping[str, bool],
) -> dict[str, object]:
    symbol = str(pair.symbol)
    provider = pair.provider if isinstance(pair.provider, str) else ""
    if provider == "twelvedata" and not settings.twelve_data_api_key:
        return {
            "symbol": symbol,
            "provider": provider,
            "status": "UNAVAILABLE",
            "error": "TwelveData API credentials are not configured.",
        }

    candles_frame = await feed.fetch_candles(
        symbol,
        provider,
        timeframe="5M",
        limit=120,
    )
    if candles_frame is None or candles_frame.empty:
        return {
            "symbol": symbol,
            "provider": provider or "unconfigured",
            "status": "UNAVAILABLE",
            "error": "The configured provider returned no closed candles.",
        }
    try:
        return build_pair_snapshot(symbol, provider, candles_frame, selection)
    except (KeyError, TypeError, ValueError):
        return {
            "symbol": symbol,
            "provider": provider,
            "status": "UNAVAILABLE",
            "error": "The provider returned candle data that could not be analyzed.",
        }


@dashboard_router.websocket("/ws/dashboard")
async def stream_dashboard(websocket: WebSocket) -> None:
    await websocket.accept()
    feed = DataFeedManager()
    selection = DEFAULT_MODULE_SELECTION.copy()
    refresh_requested = asyncio.Event()
    dispatch_queue: asyncio.Queue[tuple[str, list[str]]] = asyncio.Queue()
    latest_snapshots: list[dict[str, object]] = []
    latest_selection: dict[str, bool] | None = None

    try:
        try:
            initial_message = await asyncio.wait_for(websocket.receive_json(), timeout=5)
            selection = validate_module_selection(initial_message)
        except TimeoutError:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Send the ICT module selection to start live analysis.",
                }
            )
            await websocket.close(code=1008)
            return
        except (ValueError, json.JSONDecodeError) as error:
            await websocket.send_json({"type": "error", "message": str(error)})
            await websocket.close(code=1008)
            return

        settings.enabled_ict_modules = tuple(
            module for module in DASHBOARD_MODULES if selection[module]
        )

        async def receive_controls() -> None:
            nonlocal selection
            while True:
                try:
                    message = await websocket.receive_json()
                except WebSocketDisconnect:
                    return
                except json.JSONDecodeError:
                    await websocket.send_json(
                        {"type": "error", "message": "Control message must be valid JSON."}
                    )
                    continue

                if isinstance(message, dict) and message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                if isinstance(message, dict) and message.get("type") == "refresh":
                    refresh_requested.set()
                    continue
                if isinstance(message, dict) and message.get("type") == "telegram_dispatch":
                    try:
                        dispatch = validate_telegram_dispatch(message)
                    except ValueError as error:
                        await websocket.send_json(
                            {
                                "type": "telegram_result",
                                "ok": False,
                                "message": str(error),
                                "sent": 0,
                                "total": 0,
                            }
                        )
                        continue
                    await dispatch_queue.put(dispatch)
                    refresh_requested.set()
                    continue
                try:
                    selection = validate_module_selection(message)
                except ValueError as error:
                    await websocket.send_json({"type": "error", "message": str(error)})
                    continue

                settings.enabled_ict_modules = tuple(
                    module for module in DASHBOARD_MODULES if selection[module]
                )
                refresh_requested.set()

        controls_task = asyncio.create_task(receive_controls())
        try:
            while True:
                refresh_requested.clear()
                while not dispatch_queue.empty():
                    mode, entry_ids = await dispatch_queue.get()
                    if latest_selection is None or latest_selection != selection:
                        await websocket.send_json(
                            {
                                "type": "telegram_result",
                                "ok": False,
                                "message": "Module settings changed. Wait for the latest scan before sending setups.",
                                "sent": 0,
                                "total": len(entry_ids),
                            }
                        )
                        continue
                    detected_entries = collect_detected_entries(latest_snapshots)
                    if mode == "selected":
                        selected_ids = set(entry_ids)
                        selected_entries = [
                            entry for entry in detected_entries if entry["id"] in selected_ids
                        ]
                        if len(selected_entries) != len(selected_ids):
                            await websocket.send_json(
                                {
                                    "type": "telegram_result",
                                    "ok": False,
                                    "message": "One or more selected setups are no longer active. Refresh the scan and select again.",
                                    "sent": 0,
                                    "total": len(selected_ids),
                                }
                            )
                            continue
                    else:
                        selected_entries = detected_entries

                    if not selected_entries:
                        await websocket.send_json(
                            {
                                "type": "telegram_result",
                                "ok": False,
                                "message": "There are no active detected entries to send.",
                                "sent": 0,
                                "total": 0,
                            }
                        )
                        continue

                    sent = 0
                    try:
                        notifier = TelegramNotifier()
                        await notifier.send_messages(
                            [format_detected_entry_alert(entry) for entry in selected_entries]
                        )
                    except RuntimeError as error:
                        await websocket.send_json(
                            {
                                "type": "telegram_result",
                                "ok": False,
                                "message": str(error),
                                "sent": sent,
                                "total": len(selected_entries),
                            }
                        )
                    except TelegramError as error:
                        logger.error(
                            "telegram_dashboard_dispatch_failed",
                            error_type=type(error).__name__,
                        )
                        await websocket.send_json(
                            {
                                "type": "telegram_result",
                                "ok": False,
                                "message": "Telegram delivery failed. Check backend logs and bot configuration.",
                                "sent": sent,
                                "total": len(selected_entries),
                            }
                        )
                    else:
                        sent = len(selected_entries)
                        await websocket.send_json(
                            {
                                "type": "telegram_result",
                                "ok": True,
                                "message": f"Sent {sent} detected setup{'s' if sent != 1 else ''} to Telegram.",
                                "sent": sent,
                                "total": len(selected_entries),
                            }
                        )

                scan_selection = selection.copy()
                pairs = await _configured_pairs()
                snapshots = await asyncio.gather(
                    *(_pair_update(feed, pair, scan_selection) for pair in pairs)
                )
                latest_snapshots = snapshots
                latest_selection = scan_selection
                await websocket.send_json(
                    {
                        "type": "dashboard",
                        "generated_at": datetime.now(UTC).isoformat(),
                        "scan_interval_seconds": settings.scan_interval_seconds,
                        "pairs": snapshots,
                        "entries": collect_detected_entries(snapshots),
                    }
                )
                try:
                    await asyncio.wait_for(
                        refresh_requested.wait(),
                        timeout=max(5, settings.scan_interval_seconds),
                    )
                except TimeoutError:
                    continue
        except WebSocketDisconnect:
            pass
        finally:
            controls_task.cancel()
            try:
                await controls_task
            except asyncio.CancelledError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        await feed.close()
