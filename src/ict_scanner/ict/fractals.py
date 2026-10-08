import pandas as pd

def identify_swings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifies Swing Highs and Swing Lows (5-Bar Fractal).
    A swing is confirmed 2 candles after it forms.
    df must contain High and Low columns.
    """
    # Initialize columns
    df = df.copy()
    df['Swing_High'] = False
    df['Swing_Low'] = False
    df['Swing_High_Price'] = float('nan')
    df['Swing_Low_Price'] = float('nan')
    
    highs = df['High'].values
    lows = df['Low'].values
    
    # We need at least 5 candles
    for i in range(2, len(df) - 2):
        # Swing High
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            df.loc[df.index[i], 'Swing_High'] = True
            df.loc[df.index[i], 'Swing_High_Price'] = highs[i]
            
        # Swing Low
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            df.loc[df.index[i], 'Swing_Low'] = True
            df.loc[df.index[i], 'Swing_Low_Price'] = lows[i]
            
    return df
