from datetime import UTC, datetime, timedelta

from ict_scanner.charting.renderer import render_chart
from ict_scanner.domain.enums import Direction, Session, SetupStatus, Timeframe
from ict_scanner.domain.models import Candle, Setup


def test_render_chart() -> None:
    now = datetime.now(UTC)
    candles = [
        Candle(
            timestamp=now - timedelta(minutes=(10-i)*5),
            open=1.0, high=1.2, low=0.8, close=1.1, volume=100
        ) for i in range(10)
    ]
    setup = Setup(
        symbol="EUR/USD", direction=Direction.BUY, session_name=Session.LONDON,
        entry_tf=Timeframe.M5, status=SetupStatus.PENDING, sweep_level=0.5, sweep_type="SSL",
        mss_level=1.5, displacement_atr=2.0, fvg_low=0.9, fvg_high=1.0, ob_low=None, ob_high=None,
        ote_low=0.7, ote_high=0.8, range_low=0.5, range_high=1.5, entry_price=0.95, stop_loss=0.4,
        tp1=1.5, tp2=2.0, rr1=1.0, rr2=2.0, rule_score=80.0, dedupe_key="test",
        created_at=now, expires_at=now
    )
    
    png_bytes = render_chart(setup, candles)
    assert len(png_bytes) > 1000 # Should be a valid PNG
