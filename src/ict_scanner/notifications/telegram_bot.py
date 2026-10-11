import os
from collections.abc import Sequence
from datetime import UTC, datetime

import structlog
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from ict_scanner.config.settings import settings

logger = structlog.get_logger(__name__)

class TelegramNotifier:
    def __init__(self) -> None:
        self.bot: Bot | None = None
        self.chat_id = settings.telegram_chat_id
        if settings.telegram_bot_token and settings.telegram_chat_id:
            self.bot = Bot(token=settings.telegram_bot_token)
        else:
            logger.warning("telegram_credentials_not_configured")

    async def send_messages(self, messages: Sequence[str]) -> None:
        if self.bot is None or not self.chat_id:
            raise RuntimeError(
                "Telegram dispatch is unavailable: configure TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID in the backend environment."
            )
        if not messages:
            raise ValueError("At least one Telegram message is required.")

        try:
            async with self.bot:
                for message in messages:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML,
                    )
        except TelegramError as error:
            logger.error(
                "telegram_message_delivery_failed",
                error_type=type(error).__name__,
            )
            raise

    async def send_message(self, message: str) -> None:
        await self.send_messages((message,))

    async def send_alert(
        self, setup: dict[str, object], ai_evaluation: dict[str, object]
    ) -> bool:
        if not self.bot:
            logger.error("Telegram alert not sent because credentials are not configured.")
            return False

        message = (
            f"🚨 <b>ICT SETUP DETECTED: {setup.get('symbol')}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Direction: {setup.get('direction')} | Killzone: {setup.get('session_name')}\n"
            f"📊 Confluence Probability: {ai_evaluation.get('probability_score')}%\n\n"
            f"🎯 <b>Execution Levels:</b>\n"
            f"• Entry: {setup.get('entry_price'):.5f}\n"
            f"• Stop Loss: {setup.get('stop_loss'):.5f}\n"
            f"• Take Profit: {setup.get('take_profit'):.5f}\n"
            f"• Risk/Reward: 1:{setup.get('rr_ratio'):.2f}\n\n"
            f"🧠 <b>AI Technical Rationale:</b>\n"
            f"{ai_evaluation.get('thesis')}\n\n"
            f"⚠️ <b>Invalidation:</b>\n"
            f"{ai_evaluation.get('invalidation_rule', ai_evaluation.get('invalidation'))}\n\n"
            f"🕒 Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            chart_path = setup.get('chart_path')
            async with self.bot:
                if isinstance(chart_path, (str, os.PathLike)) and os.path.exists(chart_path):
                    with open(chart_path, 'rb') as photo:
                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=photo,
                            caption=message,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
            return True
        except (TelegramError, OSError, RuntimeError) as error:
            logger.error("telegram_alert_send_failed", error_type=type(error).__name__)
            return False
