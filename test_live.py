import asyncio
import logging
from ict_scanner.data.crypto_ccxt import CryptoCCXTProvider
from ict_scanner.data.candle_store import CandleStore
from ict_scanner.domain.enums import Timeframe
from ict_scanner.domain.models import Candle

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("test_live")

async def main() -> None:
    logger.info("Initializing CandleStore and CryptoCCXTProvider...")
    store = CandleStore()
    provider = CryptoCCXTProvider()
    
    await provider.connect()
    
    symbol = "BTC/USDT"
    timeframe = Timeframe.M1 # Using M1 for faster testing
    
    # Callback to handle incoming candles
    async def on_candle(sym: str, tf: Timeframe, candle: Candle) -> None:
        store.add_candle(sym, tf, candle)
        candles = store.get_candles(sym, tf)
        logger.info(f"Received Live Candle for {sym} ({tf.value}): Time={candle.timestamp}, Close={candle.close}, Vol={candle.volume}. Total in store: {len(candles)}")
        
    logger.info(f"Starting WebSocket stream for {symbol} on {timeframe.value}...")
    
    # Run the watcher as a background task
    task = asyncio.create_task(provider.watch_ohlcv_loop(symbol, timeframe, on_candle))
    
    try:
        # Let it stream for 30 seconds
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        logger.info("Streaming stopped by user.")
    finally:
        task.cancel()
        await provider.disconnect()
        logger.info("Disconnected from Binance WebSocket.")

if __name__ == "__main__":
    asyncio.run(main())
