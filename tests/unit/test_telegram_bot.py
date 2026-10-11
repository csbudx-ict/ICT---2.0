from unittest.mock import AsyncMock, Mock, call

import pytest

from ict_scanner.config.settings import settings
from ict_scanner.notifications import telegram_bot


@pytest.mark.asyncio
async def test_dashboard_message_uses_configured_telegram_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = AsyncMock()
    bot.__aenter__.return_value = bot
    bot.__aexit__.return_value = False
    bot.send_message = AsyncMock()
    bot_constructor = Mock(return_value=bot)
    monkeypatch.setattr(settings, "telegram_bot_token", "test-token")
    monkeypatch.setattr(settings, "telegram_chat_id", "test-chat")
    monkeypatch.setattr(telegram_bot, "Bot", bot_constructor)

    notifier = telegram_bot.TelegramNotifier()
    await notifier.send_messages(["<b>Test alert 1</b>", "<b>Test alert 2</b>"])

    bot_constructor.assert_called_once_with(token="test-token")
    bot.__aenter__.assert_awaited_once()
    bot.__aexit__.assert_awaited_once()
    assert bot.send_message.await_args_list == [
        call(
            chat_id="test-chat",
            text="<b>Test alert 1</b>",
            parse_mode=telegram_bot.ParseMode.HTML,
        ),
        call(
            chat_id="test-chat",
            text="<b>Test alert 2</b>",
            parse_mode=telegram_bot.ParseMode.HTML,
        ),
    ]


@pytest.mark.asyncio
async def test_dashboard_message_fails_explicitly_without_telegram_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_bot_token", "")
    monkeypatch.setattr(settings, "telegram_chat_id", "")

    notifier = telegram_bot.TelegramNotifier()

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"):
        await notifier.send_message("Not sent")
    assert await notifier.send_alert({}, {}) is False
