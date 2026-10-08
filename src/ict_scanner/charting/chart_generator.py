import os
import pandas as pd
import mplfinance as mpf
import logging

logger = logging.getLogger(__name__)

def generate_setup_chart(df: pd.DataFrame, setup: dict, setup_id: int) -> str:
    """
    Generates a dark-themed annotated chart using mplfinance and saves it.
    Returns the file path.
    """
    try:
        # Create charts directory if it doesn't exist
        chart_dir = os.path.join(os.getcwd(), 'data', 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        
        filepath = os.path.join(chart_dir, f"setup_{setup_id}.png")
        
        # Take the last 60 candles
        df_plot = df.iloc[-60:].copy()
        
        # We need to map the setup variables
        entry = setup.get('entry_price', 0)
        sl = setup.get('stop_loss', 0)
        tp = setup.get('take_profit', 0)
        sweep = setup.get('sweep_level', 0)
        fvg_low = setup.get('fvg_low', 0)
        fvg_high = setup.get('fvg_high', 0)
        direction = setup.get('direction', 'BUY')
        symbol = setup.get('symbol', 'Unknown')
        
        # Custom styling (dark theme)
        mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in', ohlc='i')
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridcolor='#222222', gridstyle=':')
        
        # Add-plots (horizontal lines for Entry, SL, TP, and Sweep)
        alines = [
            # Entry (Cyan)
            [(df_plot.index[0], entry), (df_plot.index[-1], entry)],
            # Stop Loss (Red)
            [(df_plot.index[0], sl), (df_plot.index[-1], sl)],
            # Take Profit (Green)
            [(df_plot.index[0], tp), (df_plot.index[-1], tp)],
            # Liquidity Sweep (Yellow, dotted)
            [(df_plot.index[0], sweep), (df_plot.index[-1], sweep)]
        ]
        
        aline_colors = ['cyan', 'red', '#00ff00', 'yellow']
        aline_styles = ['-', '-', '-', ':']
        
        # We want a shaded rectangle for the FVG zone. Wait, mplfinance supports fill_between
        # We can fill the area between fvg_low and fvg_high for the whole chart or a specific range.
        fill_between = dict(y1=fvg_low, y2=fvg_high, alpha=0.2, color='white')
        
        title = f"ICT Setup: {symbol} ({direction})"
        
        mpf.plot(
            df_plot,
            type='candle',
            style=s,
            title=title,
            ylabel='Price',
            alines=dict(alines=alines, colors=aline_colors, linestyle=aline_styles, linewidths=1.5),
            fill_between=fill_between,
            savefig=dict(fname=filepath, dpi=120, bbox_inches='tight')
        )
        
        return filepath
    except Exception as e:
        logger.error(f"Failed to generate chart for setup {setup_id}: {e}")
        return ""
