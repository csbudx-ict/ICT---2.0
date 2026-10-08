import os
from datetime import datetime, timedelta, UTC
from ict_scanner.domain.models import Setup, Candle
from ict_scanner.domain.enums import Direction, Session, Timeframe, SetupStatus
from ict_scanner.charting.renderer import render_chart

def main() -> None:
    print("Generating sample chart...")
    
    # Fake candles
    now = datetime.now(UTC)
    candles = []
    base_price = 1.0800
    for i in range(100):
        c = Candle(
            timestamp=now - timedelta(minutes=(100-i)*5),
            open=base_price,
            high=base_price + 0.0020,
            low=base_price - 0.0010,
            close=base_price + 0.0010,
            volume=100
        )
        candles.append(c)
        base_price += 0.0001
        
    setup = Setup(
        symbol="EUR/USD",
        direction=Direction.BUY,
        session_name=Session.LONDON,
        entry_tf=Timeframe.M5,
        status=SetupStatus.PENDING,
        sweep_level=1.0750,
        sweep_type="SSL",
        mss_level=1.0850,
        displacement_atr=2.1,
        fvg_low=1.0820,
        fvg_high=1.0835,
        ob_low=1.0810,
        ob_high=1.0820,
        ote_low=1.0800,
        ote_high=1.0815,
        range_low=1.0750,
        range_high=1.0890,
        entry_price=1.08275,
        stop_loss=1.0740,
        tp1=1.0890,
        tp2=1.0950,
        rr1=2.5,
        rr2=4.0,
        rule_score=85.0,
        dedupe_key="test",
        created_at=now,
        expires_at=now + timedelta(hours=12)
    )
    
    png_bytes = render_chart(setup, candles, "(Sample)")
    
    os.makedirs("out", exist_ok=True)
    with open("out/sample_chart.png", "wb") as f:
        f.write(png_bytes)
        
    print("Sample chart saved to out/sample_chart.png")

if __name__ == "__main__":
    main()
