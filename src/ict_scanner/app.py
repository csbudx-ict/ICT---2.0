import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ict_scanner.ai.analyst import AIAnalyst
from ict_scanner.ai.gemini_provider import GeminiProvider
from ict_scanner.charting.renderer import render_chart
from ict_scanner.config.settings import settings
from ict_scanner.data.candle_store import CandleStore
from ict_scanner.data.crypto_ccxt import CryptoCCXTProvider
from ict_scanner.data.watchdog import Watchdog
from ict_scanner.db.models import Base
from ict_scanner.db.repositories import SetupRepository
from ict_scanner.domain.enums import Direction, Timeframe
from ict_scanner.domain.models import Candle
from ict_scanner.ict.engine import scan_for_setups
from ict_scanner.notifications.telegram_bot import TelegramTradeDesk

logger = structlog.get_logger()

class Application:
    def __init__(self) -> None:
        self.engine = create_async_engine(settings.database_url, echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        
        self.crypto_provider = CryptoCCXTProvider()
        self.store = CandleStore(max_len=1000)
        
        self.ai = AIAnalyst(GeminiProvider())
        self.telegram = TelegramTradeDesk()
        self.watchdog = Watchdog(stale_after_seconds=settings.stale_after_seconds)
        
        self.active_pairs = [("BTC/USDT", Timeframe.M5)]

    async def initialize(self) -> None:
        logger.info("Initializing database...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Connecting to data providers...")
        await self.crypto_provider.connect()
        self.watchdog.start()
        
        logger.info("Pre-fetching historical candles...")
        for symbol, tf in self.active_pairs:
            candles = await self.crypto_provider.fetch_historical_candles(symbol, tf, 500)
            self.store.add_candles_batch(symbol, tf, candles)
            logger.info("Fetched history", symbol=symbol, tf=tf.value, count=len(candles))

    async def on_candle(self, symbol: str, timeframe: Timeframe, candle: Candle) -> None:
        self.watchdog.ping(symbol)
        self.store.add_candle(symbol, timeframe, candle)
        
        candles = self.store.get_candles(symbol, timeframe)
        if len(candles) < 50:
            return
            
        setup = scan_for_setups(symbol, timeframe, candles, Direction.NEUTRAL)
        if not setup:
            return
            
        # Check dedupe in DB
        async with self.session_maker() as session:
            repo = SetupRepository(session)
            # Avoid dupes
            existing = await repo.get_by_dedupe_key(setup.dedupe_key)
            if existing:
                return
                
        logger.info("New ICT Setup Detected!", symbol=symbol, direction=setup.direction.value, score=setup.rule_score)
        
        # 1. Chart
        chart_bytes = render_chart(setup, candles)
        
        # 2. AI Eval
        ai_eval = await self.ai.analyze(setup)
        final_prob = self.ai.calculate_final_probability(setup, ai_eval)
        
        logger.info("AI Evaluation completed", prob=final_prob, headline=ai_eval.headline)
        
        # 3. Save to DB
        from ict_scanner.db.models import SetupModel
        async with self.session_maker() as session:
            repo = SetupRepository(session)
            db_setup = SetupModel(
                symbol=setup.symbol,
                session_name=setup.session_name.value,
                timeframe=setup.entry_tf.value,
                direction=setup.direction.value,
                sweep_level=setup.sweep_level,
                displacement_atr=setup.displacement_atr,
                fvg_high=setup.fvg_high,
                fvg_low=setup.fvg_low,
                entry_price=setup.entry_price,
                stop_loss=setup.stop_loss,
                take_profit=setup.tp1,
                rr_ratio=setup.rr1,
                dedupe_key=setup.dedupe_key,
                created_at=setup.created_at
            )
            await repo.save(db_setup)
            await session.commit()
            
        # 4. Telegram Alert
        if final_prob >= settings.min_probability_threshold:
            await self.telegram.send_setup_alert(setup, ai_eval, final_prob, chart_bytes)
            logger.info("Alert dispatched to Telegram.")
        else:
            logger.info("Setup rejected (low probability).", threshold=settings.min_probability_threshold, final=final_prob)

    async def run(self) -> None:
        await self.initialize()
        await self.telegram.send_heartbeat("ICT Scanner V2 is online and monitoring.")
        
        tasks = []
        for symbol, tf in self.active_pairs:
            t = asyncio.create_task(self.crypto_provider.watch_ohlcv_loop(symbol, tf, self.on_candle))
            tasks.append(t)
            
        logger.info("Starting live scanner loops...")
        await asyncio.gather(*tasks)

    async def shutdown(self) -> None:
        logger.info("Shutting down...")
        self.watchdog.stop()
        await self.crypto_provider.disconnect()
        await self.engine.dispose()
        await self.telegram.send_heartbeat("ICT Scanner V2 is shutting down.")

async def main() -> None:
    app = Application()
    try:
        await app.run()
    except KeyboardInterrupt:
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
