import pandas as pd
from typing import Optional, Dict

def detect_mss(df: pd.DataFrame, current_idx: int, direction: str, atr_multiplier: float = 1.5) -> Optional[Dict]:
    """
    Detects Market Structure Shift (MSS) with displacement.
    Must have a full candle body close above/below the most recent opposing swing.
    direction: 'BUY' (bullish MSS) or 'SELL' (bearish MSS).
    """
    row = df.iloc[current_idx]
    prev_df = df.iloc[:current_idx]
    
    # Calculate 14-period ATR
    if current_idx < 14:
        return None
        
    tr = pd.DataFrame()
    tr['h-l'] = df['High'] - df['Low']
    tr['h-pc'] = abs(df['High'] - df['Close'].shift(1))
    tr['l-pc'] = abs(df['Low'] - df['Close'].shift(1))
    tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr['tr'].rolling(14).mean().iloc[current_idx]
    
    body_size = abs(row['Close'] - row['Open'])
    has_displacement = body_size >= (atr * atr_multiplier)
    
    if not has_displacement:
        return None
        
    if direction == 'BUY':
        # Bullish MSS: Body close above most recent Swing High
        recent_highs = prev_df[prev_df['Swing_High'] == True]
        if not recent_highs.empty:
            last_high = recent_highs.iloc[-1]['Swing_High_Price']
            if row['Close'] > last_high:
                return {
                    'level': last_high,
                    'displacement_atr': body_size / atr
                }
                
    elif direction == 'SELL':
        # Bearish MSS: Body close below most recent Swing Low
        recent_lows = prev_df[prev_df['Swing_Low'] == True]
        if not recent_lows.empty:
            last_low = recent_lows.iloc[-1]['Swing_Low_Price']
            if row['Close'] < last_low:
                return {
                    'level': last_low,
                    'displacement_atr': body_size / atr
                }
                
    return None
