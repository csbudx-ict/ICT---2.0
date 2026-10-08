import pandas as pd
from typing import Optional, Dict

def detect_fvg(df: pd.DataFrame, current_idx: int, direction: str) -> Optional[Dict]:
    """
    Detects Fair Value Gap (FVG).
    Bullish FVG: Low[3] > High[1]
    Bearish FVG: High[3] < Low[1]
    The current_idx is Candle 3.
    """
    if current_idx < 2:
        return None
        
    candle_1 = df.iloc[current_idx - 2]
    candle_3 = df.iloc[current_idx]
    
    if direction == 'BUY':
        # Bullish FVG
        if candle_3['Low'] > candle_1['High']:
            return {
                'fvg_high': float(candle_3['Low']),
                'fvg_low': float(candle_1['High'])
            }
    elif direction == 'SELL':
        # Bearish FVG
        if candle_3['High'] < candle_1['Low']:
            return {
                'fvg_high': float(candle_1['Low']),
                'fvg_low': float(candle_3['High'])
            }
            
    return None
