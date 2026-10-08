
from matplotlib.axes import Axes

from ict_scanner.charting.primitives import draw_box, draw_hline
from ict_scanner.charting.theme import Theme
from ict_scanner.domain.models import Setup


def draw_fvg_layer(ax: Axes, setup: Setup, num_candles: int) -> None:
    start_idx = max(0, num_candles - 50) # Approx where FVG is
    draw_box(ax, start_idx, num_candles, setup.fvg_low, setup.fvg_high, Theme.FVG_BOX, Theme.FVG_ALPHA, "FVG")

def draw_trade_levels(ax: Axes, setup: Setup, num_candles: int) -> None:
    start_idx = max(0, num_candles - 30)
    end_idx = num_candles + 10
    
    draw_hline(ax, start_idx, end_idx, setup.entry_price, Theme.ENTRY_LINE, f"ENTRY {setup.entry_price:.5f}")
    draw_hline(ax, start_idx, end_idx, setup.stop_loss, Theme.SL_LINE, f"SL {setup.stop_loss:.5f}")
    draw_hline(ax, start_idx, end_idx, setup.tp1, Theme.TP_LINE, f"TP1 {setup.tp1:.5f}")
    draw_hline(ax, start_idx, end_idx, setup.tp2, Theme.TP_LINE, f"TP2 {setup.tp2:.5f}")
    
def draw_premium_discount(ax: Axes, setup: Setup, num_candles: int) -> None:
    eq = (setup.range_low + setup.range_high) / 2.0
    start_idx = max(0, num_candles - 60)
    
    draw_box(ax, start_idx, num_candles, eq, setup.range_high, Theme.PREMIUM_ZONE, Theme.ZONE_ALPHA, "PREMIUM")
    draw_box(ax, start_idx, num_candles, setup.range_low, eq, Theme.DISCOUNT_ZONE, Theme.ZONE_ALPHA, "DISCOUNT")
    draw_hline(ax, start_idx, num_candles, eq, Theme.TEXT_COLOR, "EQ", "--")
