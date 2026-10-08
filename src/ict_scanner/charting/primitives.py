from matplotlib.axes import Axes


def draw_box(ax: Axes, x_start: int, x_end: int, y_low: float, y_high: float, color: str, alpha: float, label: str) -> None:
    width = x_end - x_start
    height = y_high - y_low
    rect = ax.add_patch(
        __import__("matplotlib.patches").patches.Rectangle(
            (x_start, y_low), width, height, facecolor=color, alpha=alpha, edgecolor="none", zorder=1
        )
    )
    if label:
        ax.text(x_start + width/2, y_high, label, color=color, ha="center", va="bottom", fontsize=8, zorder=5)

def draw_hline(ax: Axes, x_start: int, x_end: int, y: float, color: str, label: str, style: str = "-") -> None:
    ax.plot([x_start, x_end], [y, y], color=color, linestyle=style, linewidth=1.5, zorder=3)
    if label:
        ax.text(x_end, y, f" {label}", color=color, ha="left", va="center", fontsize=8, zorder=5)
