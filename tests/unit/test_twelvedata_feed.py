from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from ict_scanner.config.settings import settings
from ict_scanner.orchestrator import data_feed
from ict_scanner.orchestrator.data_feed import DataFeedManager


@pytest.mark.asyncio
async def test_twelvedata_candles_keep_closed_bars_and_drop_forming_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 11, 5, 2, 30, tzinfo=tz or UTC)

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "values": [
            {
                "datetime": "2026-10-11 05:02:00",
                "open": "1.3",
                "high": "1.4",
                "low": "1.2",
                "close": "1.35",
                "volume": "0",
            },
            {
                "datetime": "2026-10-11 05:01:00",
                "open": "1.2",
                "high": "1.3",
                "low": "1.1",
                "close": "1.25",
                "volume": "0",
            },
            {
                "datetime": "2026-10-11 05:00:00",
                "open": "1.1",
                "high": "1.2",
                "low": "1.0",
                "close": "1.15",
                "volume": "0",
            },
        ]
    }
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    monkeypatch.setattr(data_feed, "datetime", FrozenDateTime)
    monkeypatch.setattr(data_feed.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(settings, "twelve_data_api_key", "test-key-not-printed")
    feed = object.__new__(DataFeedManager)

    result = await feed.fetch_twelvedata_candles("EUR/USD", "1min", limit=3)

    assert result is not None
    assert list(result["Close"]) == [1.15, 1.25]
    assert result.index.tz is not None
    request = client.get.await_args
    assert request.args[0] == "https://api.twelvedata.com/time_series"
    assert request.kwargs["params"] == {
        "symbol": "EUR/USD",
        "interval": "1min",
        "outputsize": 3,
        "timezone": "UTC",
        "apikey": "test-key-not-printed",
    }


@pytest.mark.asyncio
async def test_twelvedata_missing_key_does_not_make_http_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "twelve_data_api_key", "")
    feed = object.__new__(DataFeedManager)

    assert await feed.fetch_twelvedata_candles("EUR/USD", "1min") is None
