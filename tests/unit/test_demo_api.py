from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import pandas as pd
from ict_scanner.api import demo_routes
from ict_scanner.api.demo import app
from ict_scanner.config.settings import settings
from ict_scanner.ict.fibonacci import FIBONACCI_LEVELS


def _provider_frame() -> pd.DataFrame:
    timestamps = [
        datetime(2026, 10, 10, 12, tzinfo=UTC) + timedelta(minutes=index) for index in range(30)
    ]
    prices = [1.1 + index * 0.0001 for index in range(30)]
    return pd.DataFrame(
        [
            {
                "Open": price,
                "High": price + 0.0002,
                "Low": price - 0.0002,
                "Close": price + 0.0001,
                "Volume": 0.0,
            }
            for price in prices
        ],
        index=timestamps,
    )


class StubTwelveDataFeed:
    def __init__(self) -> None:
        self.requested: list[tuple[str, str, int]] = []

    async def fetch_twelvedata_candles(
        self, symbol: str, timeframe: str, limit: int = 100
    ) -> pd.DataFrame:
        self.requested.append((symbol, timeframe, limit))
        return _provider_frame()

    async def close(self) -> None:
        return None


def test_websocket_streams_provider_candles_for_all_three_markets(monkeypatch) -> None:
    feed = StubTwelveDataFeed()
    monkeypatch.setattr(settings, "twelve_data_api_key", "test-key-not-printed")
    monkeypatch.setattr(demo_routes, "DataFeedManager", lambda: feed)

    with TestClient(app) as client, client.websocket_connect("/api/ws/demo/eurusd") as websocket:
        websocket.send_json(
            {"type": "configure", "modules": {module: True for module in demo_routes.LIVE_MODULES}}
        )
        update = websocket.receive_json()

    assert update["type"] == "market_update"
    assert update["provider"] == "Twelve Data"
    assert [item["symbol"] for item in update["symbols"]] == [
        "EUR/USD",
        "GBP/USD",
        "XAU/USD",
    ]
    assert all(item["status"] == "live" for item in update["symbols"])
    assert all(item["timeframe"] == "1min" for item in update["symbols"])
    assert all(item["candle"]["close"] == item["price"] for item in update["symbols"])
    assert all(set(item["modules"]) == set(demo_routes.LIVE_MODULES) for item in update["symbols"])
    assert feed.requested == [(symbol, "1min", 120) for symbol in demo_routes.LIVE_SYMBOLS]
    assert FIBONACCI_LEVELS == (0, 1, 0.618, 0.705, 0.79, -1, -0.62, -0.27, 0.5)


def test_missing_twelve_data_key_is_reported_without_synthetic_fallback(monkeypatch) -> None:
    feed = StubTwelveDataFeed()
    monkeypatch.setattr(settings, "twelve_data_api_key", "")
    monkeypatch.setattr(demo_routes, "DataFeedManager", lambda: feed)

    with TestClient(app) as client, client.websocket_connect("/api/ws/demo/eurusd") as websocket:
        websocket.send_json(
            {"type": "configure", "modules": {module: True for module in demo_routes.LIVE_MODULES}}
        )
        update = websocket.receive_json()

    assert all(item["status"] == "unavailable" for item in update["symbols"])
    assert all("TWELVE_DATA_API_KEY" in item["error"] for item in update["symbols"])
    assert feed.requested == []


def test_websocket_applies_toggles_without_spending_another_provider_poll(
    monkeypatch,
) -> None:
    feed = StubTwelveDataFeed()
    monkeypatch.setattr(settings, "twelve_data_api_key", "test-key-not-printed")
    monkeypatch.setattr(demo_routes, "DataFeedManager", lambda: feed)
    all_enabled = {module: True for module in demo_routes.LIVE_MODULES}
    disabled = {module: False for module in demo_routes.LIVE_MODULES}

    with TestClient(app) as client, client.websocket_connect("/api/ws/live-market") as websocket:
        websocket.send_json({"type": "configure", "modules": all_enabled})
        websocket.receive_json()
        websocket.send_json({"type": "configure", "modules": disabled})
        update = websocket.receive_json()

    assert all(
        not module["enabled"] and module["signal"] is None
        for item in update["symbols"]
        for module in item["modules"].values()
    )
    assert feed.requested == [(symbol, "1min", 120) for symbol in demo_routes.LIVE_SYMBOLS]


@pytest.mark.asyncio
async def test_invalid_websocket_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="every ICT module toggle"):
        demo_routes._validate_module_selection({"type": "configure", "modules": {}})
    with pytest.raises(ValueError, match="booleans"):
        demo_routes._validate_module_selection(
            {
                "type": "configure",
                "modules": {**demo_routes.DEFAULT_ENABLED_MODULES, "unicorn_setup": 1},
            }
        )
