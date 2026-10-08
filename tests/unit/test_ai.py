from datetime import UTC, datetime

import pytest

from ict_scanner.ai.analyst import AIAnalyst
from ict_scanner.ai.providers import DummyAIProvider
from ict_scanner.domain.enums import Direction, Session, SetupStatus, Timeframe
from ict_scanner.domain.models import Setup


@pytest.mark.asyncio
async def test_ai_analyst() -> None:
    provider = DummyAIProvider()
    analyst = AIAnalyst(provider)
    
    setup = Setup(
        symbol="EUR/USD", direction=Direction.BUY, session_name=Session.LONDON,
        entry_tf=Timeframe.M5, status=SetupStatus.PENDING, sweep_level=0.5, sweep_type="SSL",
        mss_level=1.5, displacement_atr=2.0, fvg_low=0.9, fvg_high=1.0, ob_low=None, ob_high=None,
        ote_low=0.7, ote_high=0.8, range_low=0.5, range_high=1.5, entry_price=0.95, stop_loss=0.4,
        tp1=1.5, tp2=2.0, rr1=1.0, rr2=2.0, rule_score=80.0, dedupe_key="test",
        created_at=datetime.now(UTC), expires_at=datetime.now(UTC)
    )
    
    eval_result = await analyst.analyze(setup)
    assert eval_result.probability_score == 85
    assert eval_result.market_bias == "Bullish"
    
    final_prob = analyst.calculate_final_probability(setup, eval_result)
    assert final_prob > 0
