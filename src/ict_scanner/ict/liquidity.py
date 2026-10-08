import pandas as pd
from typing import Optional, Dict

def detect_liquidity_sweep(df: pd.DataFrame, current_idx: int) -> Optional[Dict]:
    """
    Detects if the candle at current_idx swept a previous swing high/low.
    Sweep means wick exceeded the level, but body closed within the level.
    """
    row = df.iloc[current_idx]
    
    # Look back for previous swing highs/lows before current_idx
    prev_df = df.iloc[:current_idx]
    
    # Check for BSL (Bearish Sweep of Swing High)
    recent_highs = prev_df[prev_df['Swing_High'] == True]
    if not recent_highs.empty:
        last_high = recent_highs.iloc[-1]['Swing_High_Price']
        # Wick exceeded high, but close is strictly below it
        if row['High'] > last_high and row['Close'] < last_high:
            return {
                'type': 'BSL_SWEEP',
                'level': last_high,
                'direction': 'SELL'
            }
            
    # Check for SSL (Bullish Sweep of Swing Low)
    recent_lows = prev_df[prev_df['Swing_Low'] == True]
    if not recent_lows.empty:
        last_low = recent_lows.iloc[-1]['Swing_Low_Price']
        # Wick exceeded low, but close is strictly above it
        if row['Low'] < last_low and row['Close'] > last_low:
            return {
                'type': 'SSL_SWEEP',
                'level': last_low,
                'direction': 'BUY'
            }
            
    return None
