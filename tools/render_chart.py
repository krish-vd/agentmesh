"""
Renders a 12-month price chart with real technical context for the PDF
report: 52-week high/low reference lines, a rolling volatility band,
50-day MA, and volume -- styled to match the report's navy/charcoal
institutional palette.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import pandas as pd
import os
from pathlib import Path

# -- Palette: matches report.py's institutional navy/charcoal theme -----------
C_BG       = "#FFFFFF"
C_GRID     = "#E5E8EE"
C_AXIS     = "#D7DBE2"
C_MUTED    = "#6B7280"
C_TEXT     = "#16181D"
C_LINE     = "#1B2A4A"   # navy price line
C_MA       = "#9C7A1E"   # gold 50-day MA
C_BAND     = "#1B2A4A"   # navy, low alpha, for volatility band
C_HI       = "#0F7A4D"   # green 52w high
C_LO       = "#B3261E"   # red 52w low
C_VOL_UP   = "#0F7A4D"
C_VOL_DOWN = "#B3261E"

_FONT_DIRS = [
    "/System/Library/Fonts/Supplemental/",
    "/usr/share/fonts/truetype/dejavu/",
    "/opt/homebrew/share/fonts/",
    "/Library/Fonts/",
    str(Path.home() / "Library/Fonts/"),
]


def _register_font(filenames):
    for d in _FONT_DIRS:
        for filename in filenames:
            path = os.path.join(d, filename)
            if os.path.isfile(path) and not path.endswith(".ttc"):
                fm.fontManager.addfont(path)
                return fm.FontProperties(fname=path).get_name()
    return None


_sans_name = _register_font(["Arial.ttf", "DejaVuSans.ttf"])
FONT_FAMILY = _sans_name or "DejaVu Sans"


def render_chart(ticker: str, hist_df: pd.DataFrame,
                 output_path: str = "outputs/chart.png") -> str:
    """Render an institutional-style price chart. Returns path or error string."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        plt.rcParams["font.family"] = FONT_FAMILY

        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 5.2),
            facecolor=C_BG,
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06}
        )

        close = hist_df["close"]
        hi_52w, lo_52w = close.max(), close.min()

        # -- Volatility band: rolling 20-day mean +/- 1 std dev -----------------
        roll_mean = close.rolling(20).mean()
        roll_std  = close.rolling(20).std()
        ax1.fill_between(
            hist_df.index, roll_mean - roll_std, roll_mean + roll_std,
            color=C_BAND, alpha=0.06, zorder=1, label="20-day volatility band"
        )

        # -- Price line -----------------------------------------------------------
        ax1.set_facecolor(C_BG)
        ax1.plot(hist_df.index, close, color=C_LINE, linewidth=1.6, zorder=4)

        # -- 50-day MA --------------------------------------------------------------
        ma50 = close.rolling(50).mean()
        ax1.plot(hist_df.index, ma50, color=C_MA, linewidth=1,
                 linestyle="--", alpha=0.85, label="50-day MA", zorder=3)

        # -- 52-week high/low reference lines ---------------------------------------
        ax1.axhline(hi_52w, color=C_HI, linewidth=0.8, linestyle=":", alpha=0.8, zorder=2)
        ax1.axhline(lo_52w, color=C_LO, linewidth=0.8, linestyle=":", alpha=0.8, zorder=2)
        label_box = dict(facecolor=C_BG, edgecolor="none", pad=1.5)
        ax1.text(hist_df.index[-1], hi_52w, f"  52w high {hi_52w:,.2f}",
                 color=C_HI, fontsize=7.5, va="bottom", ha="left", clip_on=False,
                 bbox=label_box)
        ax1.text(hist_df.index[-1], lo_52w, f"  52w low {lo_52w:,.2f}",
                 color=C_LO, fontsize=7.5, va="top", ha="left", clip_on=False,
                 bbox=label_box)

        ax1.set_ylabel("Price", fontsize=9, color=C_MUTED)
        ax1.tick_params(colors=C_MUTED, labelsize=8)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax1.grid(True, axis="y", color=C_GRID, linewidth=0.6, zorder=0)
        for spine in ["top", "right"]:
            ax1.spines[spine].set_visible(False)
        ax1.spines["left"].set_color(C_AXIS)
        ax1.spines["bottom"].set_color(C_AXIS)
        ax1.legend(
            fontsize=7.5, framealpha=0, loc="lower left",
            bbox_to_anchor=(0, 1.01), ncol=2, borderaxespad=0,
            handlelength=1.6, columnspacing=1.2
        )
        ax1.set_title(f"{ticker.upper()}  ·  12-month price",
                      fontsize=11, color=C_TEXT, loc="left", pad=26,
                      fontweight="bold")
        plt.setp(ax1.get_xticklabels(), visible=False)

        # -- Volume bars ------------------------------------------------------------
        ax2.set_facecolor(C_BG)
        bar_colors = [
            C_VOL_UP if c >= o else C_VOL_DOWN
            for c, o in zip(hist_df["close"], hist_df["open"])
        ]
        ax2.bar(hist_df.index, hist_df["volume"],
                color=bar_colors, alpha=0.55, width=1.5)
        ax2.set_ylabel("Vol", fontsize=8, color=C_MUTED)
        ax2.tick_params(colors=C_MUTED, labelsize=7)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax2.grid(True, axis="y", color=C_GRID, linewidth=0.6, zorder=0)
        for spine in ["top", "right"]:
            ax2.spines[spine].set_visible(False)
        ax2.spines["left"].set_color(C_AXIS)
        ax2.spines["bottom"].set_color(C_AXIS)
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1e6:.0f}M")
        )

        fig.tight_layout(pad=1.4, rect=(0, 0, 0.93, 1))
        fig.savefig(output_path, dpi=150, facecolor=C_BG)
        plt.close(fig)
        return output_path

    except Exception as e:
        plt.close("all")
        return f"ERROR: {e}"


if __name__ == "__main__":
    import sys
    import yfinance as yf
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    df = yf.Ticker(ticker).history(period="1y")
    df.columns = [c.lower() for c in df.columns]
    path = render_chart(ticker, df, f"outputs/chart_{ticker}.png")
    print(f"Chart: {path}")
