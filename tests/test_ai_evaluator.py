import pytest
from unittest.mock import AsyncMock, patch
from core.ai.evaluator import AIEvaluator
from config.settings import settings

@pytest.mark.asyncio
async def test_ai_evaluator_mock():
    # Force test configuration
    settings.ai_provider = "openai"
    settings.min_probability_threshold = 75
    settings.openai_api_key = "dummy_key"
    
    # Mock setup data
    mock_setup = {
        'symbol': 'EUR/USD',
        'session_name': 'London Open',
        'direction': 'BUY',
        'sweep_level': 1.1000,
        'fvg_low': 1.1010,
        'fvg_high': 1.1020,
        'entry_price': 1.1015,
        'stop_loss': 1.0990,
        'take_profit': 1.1065,
        'rr_ratio': 2.0
    }
    
    evaluator = AIEvaluator()
    
    # Mock the AsyncOpenAI client response
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    # Return a high probability to test approval
    mock_response.choices[0].message.content = '''
    {
        "probability_score": 85,
        "market_bias": "Bullish",
        "thesis": "Strong liquidity sweep followed by displacement. Institutional sponsorship is evident.",
        "invalidation": "Price closes below the sweep level.",
        "confluence_checklist": ["Sweep", "MSS", "FVG"]
    }
    '''
    
    evaluator.client = AsyncMock()
    evaluator.client.chat.completions.create.return_value = mock_response
    
    result = await evaluator.evaluate_setup(mock_setup)
    
    assert result is not None
    assert result['probability_score'] == 85
    assert result['approved'] is True
    assert result['market_bias'] == 'Bullish'

@pytest.mark.asyncio
async def test_ai_evaluator_rejection_mock():
    # Test rejection logic when AI hallucinates approved=True but score < 75
    settings.ai_provider = "openai"
    settings.min_probability_threshold = 75
    settings.openai_api_key = "dummy_key"
    
    mock_setup = {'symbol': 'EUR/USD'}
    evaluator = AIEvaluator()
    
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = '''
    {
        "probability_score": 60,
        "approved": true,
        "market_bias": "Neutral",
        "thesis": "Weak displacement.",
        "invalidation": "N/A",
        "confluence_checklist": []
    }
    '''
    
    evaluator.client = AsyncMock()
    evaluator.client.chat.completions.create.return_value = mock_response
    
    result = await evaluator.evaluate_setup(mock_setup)
    
    assert result is not None
    assert result['probability_score'] == 60
    assert result['approved'] is False # Enforced locally despite AI saying true
