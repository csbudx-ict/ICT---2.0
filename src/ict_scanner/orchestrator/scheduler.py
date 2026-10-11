import asyncio
import logging
import traceback

from sqlalchemy.future import select

from ict_scanner.ai.evaluator import AIEvaluator
from ict_scanner.config.settings import settings
from ict_scanner.db.database import async_session
from ict_scanner.db.models import AIEvaluation, AlertLog, DetectedSetup, PairConfig, SystemHealthLog
from ict_scanner.ict.engine import scan_for_setups
from ict_scanner.notifications.email_service import EmailNotifier
from ict_scanner.notifications.telegram_bot import TelegramNotifier
from ict_scanner.orchestrator.data_feed import DataFeedManager, dataframe_to_candles
from ict_scanner.visualization.chart_generator import generate_setup_chart

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self.data_feed = DataFeedManager()
        self.ai_evaluator = AIEvaluator()
        self.telegram = TelegramNotifier()
        self.email = EmailNotifier()
        self.running = False
        self.task = None

    async def log_health(self, component: str, status: str, message: str = ""):
        async with async_session() as session:
            session.add(SystemHealthLog(component=component, status=status, message=message))
            await session.commit()

    async def dedupe_check(self, dedupe_key: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(DetectedSetup).where(DetectedSetup.dedupe_key == dedupe_key)
            )
            return result.scalars().first() is not None

    async def process_pair(self, pair: PairConfig):
        try:
            df = await self.data_feed.fetch_candles(pair.symbol, pair.provider)
            if df is None or df.empty:
                return

            setups = scan_for_setups(pair.symbol, dataframe_to_candles(df))

            for setup in setups:
                if await self.dedupe_check(setup["dedupe_key"]):
                    continue

                ai_eval = await self.ai_evaluator.evaluate_setup(setup)
                if not ai_eval:
                    continue

                # Save setup and evaluation to DB
                async with async_session() as session:
                    db_setup = DetectedSetup(**setup)
                    session.add(db_setup)
                    await session.flush()  # To get the ID

                    db_eval = AIEvaluation(
                        setup_id=db_setup.id,
                        probability_score=ai_eval.get("probability_score", 0),
                        market_bias=ai_eval.get("market_bias", "Neutral"),
                        narrative_thesis=ai_eval.get("thesis", ""),
                        invalidation_rule=ai_eval.get("invalidation", ""),
                        approved_for_alert=ai_eval.get("approved", False),
                    )
                    session.add(db_eval)
                    await session.commit()

                    if ai_eval.get("approved"):
                        # Generate Chart
                        chart_path = generate_setup_chart(df, setup, db_setup.id)
                        setup["chart_path"] = chart_path

                        # Send Telegram
                        tel_status = await self.telegram.send_alert(setup, ai_eval)
                        session.add(
                            AlertLog(
                                setup_id=db_setup.id,
                                channel="TELEGRAM",
                                status="SENT" if tel_status else "FAILED",
                            )
                        )

                        # Send Email
                        em_status = await self.email.send_alert(setup, ai_eval)
                        session.add(
                            AlertLog(
                                setup_id=db_setup.id,
                                channel="EMAIL",
                                status="SENT" if em_status else "FAILED",
                            )
                        )

                        await session.commit()

        except Exception as e:
            logger.error(f"Error processing pair {pair.symbol}: {e}")
            logger.error(traceback.format_exc())

    async def run_once(self):
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(PairConfig).where(PairConfig.is_active == True)
                )
                active_pairs = result.scalars().all()

            for pair in active_pairs:
                await self.process_pair(pair)

            await self.log_health(
                "Scheduler", "HEALTHY", "Completed manual scan cycle successfully."
            )
        except Exception as e:
            logger.error(f"Manual scan error: {e}")
            await self.log_health("Scheduler", "ERROR", str(e))

    async def loop(self):
        self.running = True
        while self.running:
            try:
                async with async_session() as session:
                    result = await session.execute(
                        select(PairConfig).where(PairConfig.is_active == True)
                    )
                    active_pairs = result.scalars().all()

                for pair in active_pairs:
                    if not self.running:
                        break
                    await self.process_pair(pair)

                await self.log_health("Scheduler", "HEALTHY", "Completed scan cycle successfully.")

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await self.log_health("Scheduler", "ERROR", str(e))

            if self.running:
                await asyncio.sleep(settings.scan_interval_seconds)

    async def start(self):
        if self.task is None:
            self.task = asyncio.create_task(self.loop())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self.data_feed.close()
