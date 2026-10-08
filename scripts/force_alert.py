import asyncio
import os
from datetime import datetime, UTC, timedelta
from ict_scanner.data.crypto_ccxt import CryptoCCXTProvider
from ict_scanner.domain.enums import Timeframe, Direction, Session, SetupStatus
from ict_scanner.domain.models import Setup
from ict_scanner.charting.renderer import render_chart
from ict_scanner.ai.analyst import AIAnalyst
from ict_scanner.ai.gemini_provider import GeminiProvider
from ict_scanner.notifications.telegram_bot import TelegramTradeDesk

async def force_alert() -> None:
    print("Fetching live market data for BTC/USDT...")
    crypto = CryptoCCXTProvider()
    await crypto.connect()
    candles = await crypto.fetch_historical_candles("BTC/USDT", Timeframe.M5, 150)
    await crypto.disconnect()
    
    print("Generating simulated ICT Setup based on current price action...")
    latest = candles[-1]
    
    # We create a simulated FVG/Sweep setup based on the last candle's price
    # so the chart looks accurate to current market data.
    base_price = latest.close
    setup = Setup(
        symbol="BTC/USDT",
        direction=Direction.BUY,
        session_name=Session.NEW_YORK_AM,
        entry_tf=Timeframe.M5,
        status=SetupStatus.PENDING,
        sweep_level=base_price * 0.995,
        sweep_type="SSL",
        mss_level=base_price * 1.002,
        displacement_atr=2.5,
        fvg_low=base_price * 0.998,
        fvg_high=base_price * 1.001,
        ob_low=base_price * 0.996,
        ob_high=base_price * 0.998,
        ote_low=base_price * 0.997,
        ote_high=base_price * 0.999,
        range_low=base_price * 0.995,
        range_high=base_price * 1.005,
        entry_price=base_price,
        stop_loss=base_price * 0.994,
        tp1=base_price * 1.006,
        tp2=base_price * 1.010,
        rr1=2.0,
        rr2=3.3,
        rule_score=92.0,
        dedupe_key=f"test_alert_{datetime.now(UTC).timestamp()}",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=4)
    )
    
    print("Rendering chart...")
    chart_bytes = render_chart(setup, candles, "(Live Test Run)")
    
    print("Querying Gemini 2.5 Flash for AI Analysis...")
    ai = AIAnalyst(GeminiProvider())
    ai_eval = await ai.analyze(setup)
    final_prob = ai.calculate_final_probability(setup, ai_eval)
    
    print("Sending alert to Telegram...")
    tg = TelegramTradeDesk()
    success = await tg.send_setup_alert(setup, ai_eval, final_prob, chart_bytes)
    
    if success:
        print("[OK] Alert sent to Telegram successfully!")
    else:
        print("[FAIL] Failed to send alert. Check Telegram credentials.")

if __name__ == "__main__":
    asyncio.run(force_alert())
