"""Shared chart style and helpers for the analyses.

The palette is the validated reference palette (colour-blind safe in its fixed
slot order); status colours are reserved for red/amber/green meaning and always
come with a label. Text is always in ink colours, never a series colour.
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.config import CHARTS_DIR, REPORTS_DIR  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
BLUE_LIGHT = "#86b6ef"   # ordinal ramp step 250: the lighter of two blues
GREY = "#b9b8b0"         # de-emphasis for context series
STATUS = {"GREEN": "#0ca30c", "AMBER": "#fab219", "RED": "#d03b3b"}
STATUS_ICON = {"GREEN": "▲", "AMBER": "●", "RED": "▼"}
FOOTER = "Kelip Bank is fictional; all data is synthetic."

FINDINGS_JSON = REPORTS_DIR / "findings.json"


def setup():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 2.4,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "legend.frameon": False,
        "svg.hashsalt": "kelip",
    })


def new_figure(nrows=1, ncols=1, height=5.4, **kw):
    setup()
    fig, axes = plt.subplots(nrows, ncols, figsize=(10, height), **kw)
    return fig, axes


def style_axis(ax, grid_axis="y"):
    if grid_axis in ("x", "y", "both"):
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(length=0)


def titles(fig, title, subtitle, extra_top=0.0):
    """Title (the takeaway), subtitle and footer, wrapped to the figure width.

    The plot area is pushed down to sit below the header, however many lines it takes.
    """
    import textwrap

    width_in, height_in = fig.get_size_inches()
    t_lines = textwrap.wrap(title, width=int(width_in * 8.2))
    s_lines = textwrap.wrap(subtitle, width=int(width_in * 11.2))
    top_in = 0.18
    fig.text(0.012, 1 - top_in / height_in, "\n".join(t_lines), ha="left", va="top", fontsize=14, color=INK,
             weight="bold", linespacing=1.25)
    sub_y_in = top_in + len(t_lines) * 0.27 + 0.08
    fig.text(0.012, 1 - sub_y_in / height_in, "\n".join(s_lines), ha="left", va="top", fontsize=10.5,
             color=INK_2, linespacing=1.3)
    header_in = sub_y_in + len(s_lines) * 0.2 + 0.35 + extra_top
    fig.subplots_adjust(top=1 - header_in / height_in)
    fig.text(0.012, 0.015, FOOTER, ha="left", va="bottom", fontsize=8.5, color=MUTED)


def save(fig, name):
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    fig.savefig(path, dpi=160, facecolor=SURFACE, metadata={"Software": None})
    plt.close(fig)
    return path


def pct(x, digits=1):
    return f"{x * 100:.{digits}f}%"


def rm(x, digits=0):
    return f"RM{x:,.{digits}f}"


def rm_m(x, digits=1):
    return f"RM{x / 1e6:,.{digits}f}m"


def number_word(n):
    """Small whole numbers as words, as they read in a sentence."""
    words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    return words[n] if 0 <= n < len(words) else f"{n:,}"


def write_findings(findings):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FINDINGS_JSON.write_text(json.dumps(findings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
