import logging
from telegram import Bot
from telegram.constants import ParseMode
from ict_scanner.config.settings import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot = None
        if settings.telegram_bot_token and settings.telegram_chat_id:
            self.bot = Bot(token=settings.telegram_bot_token)
        else:
            logger.warning("Telegram credentials not configured. Telegram alerts will be logged but not sent.")

    async def send_alert(self, setup: dict, ai_evaluation: dict) -> bool:
        if not self.bot:
            logger.info("MOCK TELEGRAM ALERT:")
            logger.info(f"Symbol: {setup.get('symbol')}, Direction: {setup.get('direction')}")
            return True

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
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            chart_path = setup.get('chart_path')
            import os
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=settings.telegram_chat_id,
                        photo=photo,
                        caption=message,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await self.bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
