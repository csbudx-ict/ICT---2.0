import ccxt.async_support as ccxt
import httpx
import pandas as pd
from typing import Dict, Optional
import asyncio
import logging
from ict_scanner.config.settings import settings
from datetime import timezone

logger = logging.getLogger(__name__)

class DataFeedManager:
    def __init__(self):
        self.crypto_exchange = getattr(ccxt, settings.crypto_exchange)()
        self.cache: Dict[str, pd.DataFrame] = {}
        
    async def fetch_crypto_candles(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            ccxt_tf = timeframe.lower()
            # Drop the current unclosed candle by fetching limit+1 and dropping the last
            ohlcv = await self.crypto_exchange.fetch_ohlcv(symbol, ccxt_tf, limit=limit + 1)
            if not ohlcv or len(ohlcv) < 2:
                return None
                
            # Drop the last candle (forming)
            ohlcv = ohlcv[:-1]
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return None
            
    async def fetch_twelvedata_candles(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        if not settings.twelve_data_api_key:
            logger.error("TwelveData API key missing.")
            return None
            
        # mapping timeframe for TwelveData (1D -> 1day, 4H -> 4h, 15M -> 15min, 5M -> 5min)
        td_tf = timeframe.replace('M', 'min').replace('H', 'h').replace('D', 'day')
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={td_tf}&outputsize={limit + 1}&apikey={settings.twelve_data_api_key}"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
                
            if 'values' not in data:
                logger.error(f"TwelveData error for {symbol}: {data}")
                return None
                
            df = pd.DataFrame(data['values'])
            df = df.rename(columns={
                'datetime': 'timestamp',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # Ensure it is UTC
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            df.set_index('timestamp', inplace=True)
            
            # Convert types
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col].astype(float)
            if 'Volume' in df.columns:
                df['Volume'] = df['Volume'].astype(float)
                
            # Sort chronologically (TwelveData returns newest first)
            df = df.sort_index()
            
            # Drop the current unclosed candle
            df = df.iloc[:-1]
            
            return df
        except Exception as e:
            logger.error(f"Error fetching TwelveData for {symbol}: {e}")
            return None

    async def fetch_candles(self, symbol: str, provider: str, timeframe: str = "5M", limit: int = 100) -> Optional[pd.DataFrame]:
        if provider == "ccxt":
            return await self.fetch_crypto_candles(symbol, timeframe, limit)
        elif provider == "twelvedata":
            return await self.fetch_twelvedata_candles(symbol, timeframe, limit)
        else:
            logger.error(f"Unknown provider: {provider}")
            return None
            
    async def close(self):
        await self.crypto_exchange.close()
