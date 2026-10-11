from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from telegram.error import TelegramError

import pandas as pd
from fastapi import FastAPI
from ict_scanner.api import dashboard_routes
from ict_scanner.api.dashboard_routes import (
    DASHBOARD_MODULES,
    _pair_update,
    build_pair_snapshot,
    collect_detected_entries,
    validate_module_selection,
    validate_telegram_dispatch,
)
from ict_scanner.api.demo import app as demo_app
from ict_scanner.config.settings import settings
from ict_scanner.orchestrator.data_feed import dataframe_to_candles


def test_dashboard_configuration_requires_each_boolean_module() -> None:
    selection = {module: True for module in DASHBOARD_MODULES}

    assert validate_module_selection({"type": "configure", "modules": selection}) == selection

    with pytest.raises(ValueError, match="all ICT module toggles"):
        validate_module_selection({"type": "configure", "modules": {}})
    with pytest.raises(ValueError, match="booleans"):
        validate_module_selection({"type": "configure", "modules": {**selection, "fvg": "true"}})


def test_dashboard_detected_entries_are_stable_and_prioritized() -> None:
    pairs = [
        {
            "symbol": "EUR/USD",
            "provider": "twelvedata",
            "status": "CONNECTED",
            "timestamp": "2026-01-01T12:00:00+00:00",
            "modules": {
                module: {
                    "enabled": True,
                    "signal": {
                        "direction": "BUY",
                        "timestamp": "2026-01-01T12:00:00+00:00",
                        "fvg_midpoint": 1.1,
                        "displacement_atr": 1.4,
                    },
                }
                for module in ("unicorn_setup", "institutional_order_block", "silver_bullet_fvg")
            },
        }
    ]

    entries = collect_detected_entries(pairs)

    assert [entry["module"] for entry in entries] == [
        "unicorn_setup",
        "institutional_order_block",
        "silver_bullet_fvg",
    ]
    assert entries[0]["entry"] == 1.1
    assert entries[0]["id"] == collect_detected_entries(pairs)[0]["id"]
    assert all(len(entry["id"]) == 20 for entry in entries)


def test_telegram_dispatch_only_allows_up_to_two_selected_entries() -> None:
    assert validate_telegram_dispatch({"type": "telegram_dispatch", "mode": "all"}) == ("all", [])
    assert validate_telegram_dispatch(
        {"type": "telegram_dispatch", "mode": "selected", "entry_ids": ["a" * 20]}
    ) == ("selected", ["a" * 20])
    with pytest.raises(ValueError, match="maximum of two"):
        validate_telegram_dispatch(
            {
                "type": "telegram_dispatch",
                "mode": "selected",
                "entry_ids": ["a" * 20, "b" * 20, "c" * 20],
            }
        )


def test_existing_demo_api_also_serves_the_live_dashboard_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubFeed:
        async def close(self) -> None:
            return None

    monkeypatch.setattr(dashboard_routes, "DataFeedManager", StubFeed)
    monkeypatch.setattr(dashboard_routes, "_configured_pairs", AsyncMock(return_value=[]))
    selection = {module: False for module in DASHBOARD_MODULES}

    with (
        TestClient(demo_app) as client,
        client.websocket_connect("/api/ws/dashboard") as websocket,
    ):
        websocket.send_json({"type": "configure", "modules": selection})
        message = websocket.receive_json()
        assert message["type"] == "dashboard"
        assert message["pairs"] == []
        assert message["entries"] == []
        assert isinstance(message["generated_at"], str)
        assert isinstance(message["scan_interval_seconds"], int)


def test_dashboard_websocket_recalculates_after_module_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubFeed:
        async def close(self) -> None:
            return None

    monkeypatch.setattr(dashboard_routes, "DataFeedManager", StubFeed)
    monkeypatch.setattr(dashboard_routes, "_configured_pairs", AsyncMock(return_value=[]))
    app = FastAPI()
    app.include_router(dashboard_routes.dashboard_router)
    selection = {module: False for module in DASHBOARD_MODULES}

    with TestClient(app) as client, client.websocket_connect("/ws/dashboard") as websocket:
        websocket.send_json({"type": "configure", "modules": selection})
        initial_update = websocket.receive_json()
        assert initial_update["type"] == "dashboard"
        assert initial_update["pairs"] == []
        assert initial_update["entries"] == []

        selection["fvg"] = True
        websocket.send_json({"type": "configure", "modules": selection})
        updated = websocket.receive_json()
        assert updated["type"] == "dashboard"
        assert dashboard_routes.settings.enabled_ict_modules == ("fvg",)


def test_dashboard_websocket_answers_heartbeat_ping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubFeed:
        async def close(self) -> None:
            return None

    monkeypatch.setattr(dashboard_routes, "DataFeedManager", StubFeed)
    monkeypatch.setattr(dashboard_routes, "_configured_pairs", AsyncMock(return_value=[]))
    app = FastAPI()
    app.include_router(dashboard_routes.dashboard_router)

    with TestClient(app) as client, client.websocket_connect("/ws/dashboard") as websocket:
        websocket.send_json(
            {"type": "configure", "modules": {module: True for module in DASHBOARD_MODULES}}
        )
        assert websocket.receive_json()["type"] == "dashboard"
        websocket.send_json({"type": "ping"})

        assert websocket.receive_json() == {"type": "pong"}


@pytest.mark.parametrize("mode", ["all", "selected"])
def test_dashboard_websocket_dispatches_active_entries_to_telegram(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubFeed:
        async def close(self) -> None:
            return None

    class StubNotifier:
        send_messages = AsyncMock()

    signal = {
        "direction": "BUY",
        "timestamp": "2026-01-01T12:00:00+00:00",
        "retracement_entry": 1.105,
        "low": 1.1,
        "high": 1.11,
        "mean_threshold": 1.105,
        "displacement_atr": 1.8,
    }
    snapshot = {
        "symbol": "EUR/USD",
        "provider": "twelvedata",
        "status": "CONNECTED",
        "timestamp": "2026-01-01T12:00:00+00:00",
        "modules": {
            module: {
                "enabled": module == "institutional_order_block",
                "signal": signal if module == "institutional_order_block" else None,
            }
            for module in dashboard_routes.ENTRY_MODULES
        },
    }
    monkeypatch.setattr(dashboard_routes, "DataFeedManager", StubFeed)
    monkeypatch.setattr(
        dashboard_routes,
        "_configured_pairs",
        AsyncMock(return_value=[SimpleNamespace(symbol="EUR/USD", provider="twelvedata")]),
    )
    monkeypatch.setattr(dashboard_routes, "_pair_update", AsyncMock(return_value=snapshot))
    monkeypatch.setattr(dashboard_routes, "TelegramNotifier", lambda: StubNotifier())
    app = FastAPI()
    app.include_router(dashboard_routes.dashboard_router)

    with TestClient(app) as client, client.websocket_connect("/ws/dashboard") as websocket:
        websocket.send_json(
            {"type": "configure", "modules": {module: True for module in DASHBOARD_MODULES}}
        )
        initial = websocket.receive_json()
        assert len(initial["entries"]) == 1
        dispatch: dict[str, object] = {"type": "telegram_dispatch", "mode": mode}
        if mode == "selected":
            dispatch["entry_ids"] = [initial["entries"][0]["id"]]
        websocket.send_json(dispatch)
        result = websocket.receive_json()

    assert result["type"] == "telegram_result"
    assert result["ok"] is True
    assert result["sent"] == 1
    StubNotifier.send_messages.assert_awaited_once()
    assert len(StubNotifier.send_messages.await_args.args[0]) == 1
    assert "EUR/USD" in StubNotifier.send_messages.await_args.args[0][0]


@pytest.mark.parametrize(
    ("dispatch_error", "expected_message"),
    [
        (RuntimeError("configure Telegram credentials"), "configure Telegram credentials"),
        (TelegramError("delivery failed"), "Telegram delivery failed"),
    ],
)
def test_dashboard_websocket_reports_telegram_dispatch_failures(
    dispatch_error: Exception,
    expected_message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubFeed:
        async def close(self) -> None:
            return None

    class StubNotifier:
        send_messages = AsyncMock(side_effect=dispatch_error)

    signal = {
        "direction": "BUY",
        "timestamp": "2026-01-01T12:00:00+00:00",
        "retracement_entry": 1.105,
    }
    snapshot = {
        "symbol": "EUR/USD",
        "provider": "twelvedata",
        "status": "CONNECTED",
        "timestamp": "2026-01-01T12:00:00+00:00",
        "modules": {
            module: {
                "enabled": module == "institutional_order_block",
                "signal": signal if module == "institutional_order_block" else None,
            }
            for module in dashboard_routes.ENTRY_MODULES
        },
    }
    monkeypatch.setattr(dashboard_routes, "DataFeedManager", StubFeed)
    monkeypatch.setattr(
        dashboard_routes,
        "_configured_pairs",
        AsyncMock(return_value=[SimpleNamespace(symbol="EUR/USD", provider="twelvedata")]),
    )
    monkeypatch.setattr(dashboard_routes, "_pair_update", AsyncMock(return_value=snapshot))
    monkeypatch.setattr(dashboard_routes, "TelegramNotifier", lambda: StubNotifier())
    app = FastAPI()
    app.include_router(dashboard_routes.dashboard_router)

    with TestClient(app) as client, client.websocket_connect("/ws/dashboard") as websocket:
        websocket.send_json(
            {"type": "configure", "modules": {module: True for module in DASHBOARD_MODULES}}
        )
        initial = websocket.receive_json()
        websocket.send_json({"type": "telegram_dispatch", "mode": "all"})
        result = websocket.receive_json()

    assert initial["type"] == "dashboard"
    assert result["type"] == "telegram_result"
    assert result["ok"] is False
    assert expected_message in result["message"]
    assert result["sent"] == 0


def test_provider_dataframe_converts_to_utc_domain_candles() -> None:
    timestamp = datetime(2026, 1, 1, 12)
    frame = pd.DataFrame(
        [{"Open": 10.0, "High": 12.0, "Low": 9.0, "Close": 11.0}],
        index=[timestamp],
    )

    candles = dataframe_to_candles(frame)

    assert len(candles) == 1
    assert candles[0].timestamp == timestamp.replace(tzinfo=UTC)
    assert candles[0].volume == 0.0


@pytest.mark.asyncio
async def test_missing_provider_credentials_are_reported_without_fetching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "twelve_data_api_key", "")
    feed = SimpleNamespace(fetch_candles=AsyncMock())
    pair = SimpleNamespace(symbol="EUR/USD", provider="twelvedata")

    result = await _pair_update(feed, pair, {module: True for module in DASHBOARD_MODULES})

    assert result["status"] == "UNAVAILABLE"
    assert result["error"] == "TwelveData API credentials are not configured."
    feed.fetch_candles.assert_not_awaited()


def test_dashboard_snapshot_reports_real_closed_candle_and_module_states() -> None:
    timestamps = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=5 * i) for i in range(3)]
    frame = pd.DataFrame(
        [
            {"Open": 10.0, "High": 11.0, "Low": 9.0, "Close": 10.5, "Volume": 5.0},
            {"Open": 10.5, "High": 12.0, "Low": 10.0, "Close": 11.5, "Volume": 6.0},
            {"Open": 11.5, "High": 12.5, "Low": 11.0, "Close": 12.0, "Volume": 7.0},
        ],
        index=timestamps,
    )
    selection = {module: module == "fvg" for module in DASHBOARD_MODULES}

    snapshot = build_pair_snapshot("TEST/USDT", "ccxt", frame, selection)

    assert snapshot["status"] == "CONNECTED"
    assert snapshot["timestamp"] == timestamps[-1].isoformat()
    assert snapshot["candle"] == {"open": 11.5, "high": 12.5, "low": 11.0, "close": 12.0}
    assert snapshot["modules"]["fvg"]["enabled"] is True
    assert snapshot["modules"]["silver_bullet_fvg"]["enabled"] is False
    assert snapshot["modules"]["silver_bullet_fvg"]["signal"] is None
    assert snapshot["modules"]["master_sniper"]["enabled"] is False
    assert isinstance(snapshot["advanced_ict"], dict)
