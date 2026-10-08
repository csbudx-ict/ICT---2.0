from tests.test_ict_engine import test_bullish_setup
import pandas as pd
from datetime import datetime, timedelta, timezone
from ict_scanner.ict.fractals import identify_swings
from ict_scanner.ict.liquidity import detect_liquidity_sweep
from ict_scanner.ict.structure import detect_mss
from ict_scanner.ict.imbalance import detect_fvg
from config.settings import settings

dates = [datetime(2023, 1, 1, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=5*i) for i in range(30)]
data = []
base_price = 1.1000
for i in range(30):
    open_p = base_price
    close = base_price
    high = base_price + 0.0010
    low = base_price - 0.0010
    if i == 5:
        low = base_price - 0.0030
        high = base_price - 0.0010
    if i == 15:
        low = base_price - 0.0040
        high = base_price + 0.0010
        close = base_price - 0.0020
    if i == 18:
        low = base_price
        high = base_price + 0.0030
        close = base_price + 0.0010
    if i == 20:
        low = base_price - 0.0010
        high = base_price + 0.0015
        close = base_price + 0.0010
    if i == 21:
        low = base_price + 0.0010
        high = base_price + 0.0060
        close = base_price + 0.0050
        open_p = base_price + 0.0010
    if i == 22:
        low = base_price + 0.0040
        high = base_price + 0.0070
        close = base_price + 0.0050
        open_p = base_price + 0.0040
    data.append({'Open': open_p, 'High': high, 'Low': low, 'Close': close})

df = pd.DataFrame(data, index=dates)
df = identify_swings(df)
for i in range(14, 25):
    sweep = detect_liquidity_sweep(df, i)
    if sweep:
        print(f"Sweep at {i}: {sweep}")
    if i == 21:
        print("At 21, recent highs:")
        print(df.iloc[:21][df.iloc[:21]['Swing_High'] == True][['Swing_High_Price']])
        mss = detect_mss(df, 21, 'BUY', settings.displacement_atr_multiplier)
        print(f"MSS at 21: {mss}")
    if i == 22:
        fvg = detect_fvg(df, 22, 'BUY')
        print(f"FVG at 22: {fvg}")
