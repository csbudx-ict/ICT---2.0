import pandas as pd
from datetime import datetime, timedelta, timezone
from core.ict.engine import scan_for_setups

def test_bullish_setup():
    # Create 30 mock candles
    dates = [datetime(2023, 1, 1, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=5*i) for i in range(30)]
    
    data = []
    base_price = 1.1000
    for i in range(30):
        open_p = base_price
        close = base_price
        high = base_price + 0.0010
        low = base_price - 0.0010
            
        # Create a swing low at candle 5
        if i == 5:
            low = base_price - 0.0030
            high = base_price - 0.0010
            
        # Create a sweep at candle 15
        if i == 15:
            low = base_price - 0.0040 # wick sweep
            high = base_price + 0.0010
            close = base_price - 0.0020 # close above swing low
            
        # Candle 18 will be a swing high to break
        if i == 18:
            low = base_price
            high = base_price + 0.0030 # Swing high
            close = base_price + 0.0010
            
        # Candle 20 (FVG Candle 1)
        if i == 20:
            low = base_price - 0.0010
            high = base_price + 0.0015
            close = base_price + 0.0010
            
        # Candle 21 (Displacement candle)
        if i == 21:
            low = base_price + 0.0010
            high = base_price + 0.0060
            close = base_price + 0.0050 # Close above 1.1030
            open_p = base_price + 0.0010
            
        # Candle 22 (FVG Candle 3)
        if i == 22:
            low = base_price + 0.0040 # > candle 20 high (1.1015), creating a gap
            high = base_price + 0.0070
            close = base_price + 0.0050
            open_p = base_price + 0.0040
            
        data.append({
            'Open': open_p,
            'High': high,
            'Low': low,
            'Close': close
        })
        
    df = pd.DataFrame(data, index=dates)
    setups = scan_for_setups("EUR/USD", df)
    
    assert len(setups) == 1, f"Expected 1 setup, got {len(setups)}"
    setup = setups[0]
    
    assert setup['direction'] == 'BUY'
    assert setup['symbol'] == "EUR/USD"

if __name__ == "__main__":
    test_bullish_setup()
    print("All ICT engine tests passed!")
