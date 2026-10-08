import io

import mplfinance as mpf
import pandas as pd

from ict_scanner.charting.layers import draw_fvg_layer, draw_premium_discount, draw_trade_levels
from ict_scanner.charting.theme import Theme
from ict_scanner.domain.models import Candle, Setup


def render_chart(setup: Setup, candles: list[Candle], title_suffix: str = "") -> bytes:
    df = pd.DataFrame([{
        "Date": c.timestamp,
        "Open": c.open,
        "High": c.high,
        "Low": c.low,
        "Close": c.close,
        "Volume": c.volume
    } for c in candles])
    df.set_index("Date", inplace=True)
    
    mc = mpf.make_marketcolors(
        up=Theme.CANDLE_UP, down=Theme.CANDLE_DOWN,
        edge="inherit",
        wick={"up": Theme.CANDLE_WICK_UP, "down": Theme.CANDLE_WICK_DOWN},
        volume="in"
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor=Theme.BG_COLOR,
        edgecolor=Theme.GRID_COLOR,
        figcolor=Theme.BG_COLOR,
        gridcolor=Theme.GRID_COLOR,
        gridstyle="--",
        rc={
            "xtick.color": Theme.TEXT_COLOR,
            "ytick.color": Theme.TEXT_COLOR,
            "axes.labelsize": 10,
            "axes.titlesize": 12,
        }
    )
    
    title = f"{setup.symbol} {setup.entry_tf.value} {setup.direction.value} | Score: {setup.rule_score}% {title_suffix}"
    
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=s,
        title=title,
        figsize=(16, 9),
        returnfig=True,
        tight_layout=True,
        axisoff=False
    )
    
    ax = axes[0]
    num_candles = len(candles)
    
    # Draw layers
    draw_premium_discount(ax, setup, num_candles)
    draw_fvg_layer(ax, setup, num_candles)
    draw_trade_levels(ax, setup, num_candles)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=Theme.BG_COLOR, bbox_inches="tight")
    buf.seek(0)
    return buf.read()
