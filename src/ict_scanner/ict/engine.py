import pandas as pd
import hashlib
from datetime import datetime, timezone, time
from ict_scanner.ict.fractals import identify_swings
from ict_scanner.ict.liquidity import detect_liquidity_sweep
from ict_scanner.ict.structure import detect_mss
from ict_scanner.ict.imbalance import detect_fvg
from ict_scanner.config.settings import settings
import logging

logger = logging.getLogger(__name__)

def is_in_killzone(dt: datetime) -> tuple[bool, str]:
    t = dt.time()
    if time(7, 0) <= t <= time(10, 0):
        return True, "London Open"
    if time(12, 0) <= t <= time(15, 0):
        return True, "New York AM"
    return False, ""

def generate_dedupe_key(symbol: str, direction: str, sweep_level: float, fvg_low: float, fvg_high: float) -> str:
    key_str = f"{symbol}|{direction}|{sweep_level:.5f}|{fvg_low:.5f}|{fvg_high:.5f}"
    return hashlib.md5(key_str.encode()).hexdigest()

def scan_for_setups(symbol: str, df: pd.DataFrame, timeframe: str = "5M") -> list[dict]:
    setups = []
    if len(df) < 20:
        return setups
        
    df = identify_swings(df)
    
    # State tracking
    last_sweep = None
    sweep_idx = -1
    last_mss = None
    mss_idx = -1
    
    for i in range(14, len(df)):
        dt = df.index[i]
        
        # We assume df has a DatetimeIndex
        in_kz, session_name = is_in_killzone(dt)
        if not in_kz:
            continue
            
        # 1. Check for Sweep
        sweep = detect_liquidity_sweep(df, i)
        if sweep:
            last_sweep = sweep
            sweep_idx = i
            last_mss = None
            continue
            
        # 2. If we have a recent sweep, check for MSS
        if last_sweep and (i - sweep_idx) <= settings.mss_lookback_candles:
            if not last_mss:
                mss = detect_mss(df, i, last_sweep['direction'], settings.displacement_atr_multiplier)
                if mss:
                    last_mss = mss
                    mss_idx = i
            
            # 3. If MSS, check for FVG on the candles following displacement
            if last_mss and (i - mss_idx) <= 3:
                fvg = detect_fvg(df, i, last_sweep['direction'])
                if fvg:
                    # Calculate Entry, SL, TP, RR
                    entry_price = (fvg['fvg_high'] + fvg['fvg_low']) / 2.0
                    
                    if last_sweep['direction'] == 'BUY':
                        stop_loss = last_sweep['level'] - (last_mss['displacement_atr'] * 0.1) # Buffer
                        # TP could be next opposing swing high, let's simplify for now
                        take_profit = entry_price + (entry_price - stop_loss) * settings.min_rr
                    else:
                        stop_loss = last_sweep['level'] + (last_mss['displacement_atr'] * 0.1)
                        take_profit = entry_price - (stop_loss - entry_price) * settings.min_rr
                        
                    # Avoid division by zero
                    if abs(entry_price - stop_loss) > 0:
                        rr_ratio = abs(take_profit - entry_price) / abs(entry_price - stop_loss)
                    else:
                        rr_ratio = 0
                    
                    if rr_ratio >= settings.min_rr:
                        setup = {
                            'symbol': symbol,
                            'session_name': session_name,
                            'timeframe': timeframe,
                            'direction': last_sweep['direction'],
                            'sweep_level': last_sweep['level'],
                            'displacement_atr': last_mss['displacement_atr'],
                            'fvg_high': fvg['fvg_high'],
                            'fvg_low': fvg['fvg_low'],
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'rr_ratio': rr_ratio,
                            'dedupe_key': generate_dedupe_key(symbol, last_sweep['direction'], last_sweep['level'], fvg['fvg_low'], fvg['fvg_high'])
                        }
                        setups.append(setup)
                        
                        # Reset state after setup
                        last_sweep = None
                        last_mss = None
                        
    return setups
