import logging
import re
from datetime import UTC, datetime, timedelta

import ccxt.async_support as ccxt
import httpx

import pandas as pd
from ict_scanner.config.settings import settings
from ict_scanner.domain.models import Candle

logger = logging.getLogger(__name__)


def dataframe_to_candles(df: pd.DataFrame) -> list[Candle]:
    """Convert provider OHLC data to validated UTC-aware domain candles."""
    candles = []
    for timestamp, row in df.iterrows():
        candle_time = (
            timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
        )
        if candle_time.tzinfo is None or candle_time.utcoffset() is None:
            candle_time = candle_time.replace(tzinfo=UTC)
        else:
            candle_time = candle_time.astimezone(UTC)
        candles.append(
            Candle(
                timestamp=candle_time,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0.0)),
            )
        )
    return candles


class DataFeedManager:
    def __init__(self) -> None:
        self.crypto_exchange = getattr(ccxt, settings.crypto_exchange)()
        self.cache: dict[str, pd.DataFrame] = {}

    async def fetch_crypto_candles(
        self, symbol: str, timeframe: str, limit: int = 100
    ) -> pd.DataFrame | None:
        try:
            ccxt_tf = timeframe.lower()
            # Drop the current unclosed candle by fetching limit+1 and dropping the last
            ohlcv = await self.crypto_exchange.fetch_ohlcv(symbol, ccxt_tf, limit=limit + 1)
            if not ohlcv or len(ohlcv) < 2:
                return None

            # Drop the last candle (forming)
            ohlcv = ohlcv[:-1]

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return None

    async def fetch_twelvedata_candles(
        self, symbol: str, timeframe: str, limit: int = 100
    ) -> pd.DataFrame | None:
        if not settings.twelve_data_api_key:
            logger.error("TwelveData API key missing.")
            return None

        td_tf = timeframe.lower()
        if td_tf.endswith("m") and not td_tf.endswith("min"):
            td_tf = f"{td_tf[:-1]}min"
        elif td_tf.endswith("d"):
            td_tf = f"{td_tf[:-1]}day"
        elif td_tf.endswith("h"):
            td_tf = f"{td_tf[:-1]}h"
        interval_match = re.fullmatch(r"(\d+)(min|h|day)", td_tf)
        if interval_match is None:
            raise ValueError(f"Unsupported TwelveData candle interval: {timeframe}")

        interval_amount = int(interval_match.group(1))
        if interval_amount <= 0:
            raise ValueError("TwelveData candle interval must be positive")
        unit = interval_match.group(2)
        interval = timedelta(
            minutes=interval_amount
            if unit == "min"
            else interval_amount * 60
            if unit == "h"
            else interval_amount * 1440
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.twelvedata.com/time_series",
                    params={
                        "symbol": symbol,
                        "interval": td_tf,
                        "outputsize": limit,
                        "timezone": "UTC",
                        "apikey": settings.twelve_data_api_key,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

            if "values" not in data:
                logger.error("TwelveData returned no candle values for %s", symbol)
                return None

            df = pd.DataFrame(data["values"])
            df = df.rename(
                columns={
                    "datetime": "timestamp",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
            else:
                df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")
            df.set_index("timestamp", inplace=True)

            for col in ["Open", "High", "Low", "Close"]:
                df[col] = df[col].astype(float)
            if "Volume" in df.columns:
                df["Volume"] = df["Volume"].astype(float)

            df = df.sort_index()
            now = pd.Timestamp(datetime.now(UTC))
            current_interval = now.floor(interval)
            df = df.loc[df.index < current_interval]
            return df.tail(limit)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            logger.error(
                "TwelveData candle request failed for %s (%s)",
                symbol,
                type(error).__name__,
            )
            return None

    async def fetch_candles(
        self, symbol: str, provider: str, timeframe: str = "5M", limit: int = 100
    ) -> pd.DataFrame | None:
        if provider == "ccxt":
            return await self.fetch_crypto_candles(symbol, timeframe, limit)
        elif provider == "twelvedata":
            return await self.fetch_twelvedata_candles(symbol, timeframe, limit)
        else:
            logger.error(f"Unknown provider: {provider}")
            return None

    async def close(self) -> None:
        await self.crypto_exchange.close()
