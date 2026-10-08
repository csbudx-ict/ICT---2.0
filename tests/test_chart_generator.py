import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.visualization.chart_generator import generate_setup_chart

def test_chart_generation():
    # Create mock OHLCV dataframe with 100 candles
    now = datetime.utcnow()
    dates = [now - timedelta(minutes=5 * i) for i in range(100, 0, -1)]
    
    # Generate some random candle data roughly around 1.1000
    np.random.seed(42)
    base_price = 1.1000
    opens = base_price + np.random.normal(0, 0.001, 100).cumsum()
    highs = opens + np.abs(np.random.normal(0, 0.001, 100))
    lows = opens - np.abs(np.random.normal(0, 0.001, 100))
    closes = opens + np.random.normal(0, 0.001, 100)
    
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': np.random.randint(100, 1000, 100)
    }, index=pd.DatetimeIndex(dates))
    
    # Mock setup dict
    setup = {
        'symbol': 'EUR/USD',
        'direction': 'BUY',
        'entry_price': opens[-1],
        'stop_loss': opens[-1] - 0.0020,
        'take_profit': opens[-1] + 0.0040,
        'sweep_level': opens[-1] - 0.0015,
        'fvg_low': opens[-1] - 0.0005,
        'fvg_high': opens[-1] + 0.0005
    }
    
    filepath = generate_setup_chart(df, setup, 9999)
    assert filepath is not None
    assert os.path.exists(filepath)
    print(f"Chart generated successfully: {filepath}")

if __name__ == "__main__":
    test_chart_generation()
