"""A static picture of the dashboard's Executive page, for the README and the insights report.

Six tiles, one per scorecard KPI: the latest value, plan and % of plan, the
status as an icon and a word (never colour alone), and a small line of actual
against plan. Each small chart has its own scale, so read the lines for shape,
not for comparison between tiles.
"""

import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

from src.analysis import common as C

STATUS_WORD = {"GREEN": "On plan", "AMBER": "Watch", "RED": "Off plan"}
STATUS_TINT = {"GREEN": "#ddf2dd", "AMBER": "#fef0cc", "RED": "#f8dede"}
# How each KPI reads as the subject of a sentence, and whether it takes "are"
SUBJECT = {"K02": ("new customers", True), "K07": ("monthly active customers", True),
           "K13": ("total deposits", True), "K14": ("the CASA ratio", False),
           "K15": ("cost of funds", False), "K19": ("PAR30", False)}


def show(value, unit, kpi_id):
    if unit == "count":
        return f"{value:,.0f}"
    if unit == "pct":
        return f"{value * 100:.2f}%" if kpi_id in ("K15", "K19") else f"{value * 100:.1f}%"
    return C.rm_m(value)


def headline(latest):
    month = f"{latest['month_start'].iloc[0]:%B %Y}"
    on = int((latest["status"] == "GREEN").sum())
    total = len(latest)
    others = latest[latest["status"] != "GREEN"]
    if others.empty:
        return f"{month}: all {C.number_word(total)} scorecard KPIs are on plan"
    parts = []
    for r in others.itertuples():
        subject, plural = SUBJECT.get(r.kpi_id, (r.kpi_name, False))
        word = "just outside plan" if r.status == "AMBER" else "off plan"
        parts.append(f"{subject} {'are' if plural else 'is'} {word} ({show(r.actual, r.unit, r.kpi_id)} against "
                     f"{show(r.plan, r.unit, r.kpi_id)})")
    return (f"{month}: {C.number_word(on)} of {C.number_word(total)} scorecard KPIs are on plan; "
            + "; ".join(parts))


def run(con):
    sc = con.execute("""
        SELECT s.*, c.unit AS catalog_unit
        FROM kpi.scorecard AS s JOIN reference.kpi_catalog AS c USING (kpi_id)
        ORDER BY kpi_id, month_start
    """).df()
    sc["month_start"] = pd.to_datetime(sc["month_start"])
    last_month = sc["month_start"].max()
    latest = sc[sc["month_start"] == last_month].reset_index(drop=True)

    fig = C.new_figure(height=7.4)[0]
    fig.set_size_inches(12, 7.4)
    for ax in fig.axes:
        ax.remove()
    title = headline(latest)
    C.titles(fig, title, "Kelip Bank executive scorecard: the six KPIs with a monthly plan. Status is shown as an "
                         "icon and a word; the amber band is the KPI's tolerance below plan. Each small chart has "
                         "its own scale.")
    top = fig.subplotpars.top
    left, right, gap_x, gap_y, bottom = 0.012, 0.988, 0.014, 0.03, 0.06
    tile_w = (right - left - 2 * gap_x) / 3
    tile_h = (top - bottom - gap_y) / 2

    for i, r in latest.iterrows():
        row, col = divmod(i, 3)
        x0 = left + col * (tile_w + gap_x)
        y0 = top - (row + 1) * tile_h - row * gap_y
        fig.patches.append(FancyBboxPatch((x0, y0), tile_w, tile_h, boxstyle="round,pad=0,rounding_size=0.008",
                                          transform=fig.transFigure, facecolor="#ffffff", edgecolor=C.GRID,
                                          linewidth=1, zorder=-1))
        pad = 0.014
        direction = "higher" if r["direction"] == "higher" else "lower"
        fig.text(x0 + pad, y0 + tile_h - 0.022, r["kpi_name"], fontsize=11.5, weight="bold", color=C.INK,
                 va="top")
        fig.text(x0 + pad, y0 + tile_h - 0.058, f"{r['owner']} · {direction} is better", fontsize=9,
                 color=C.MUTED, va="top")
        fig.text(x0 + pad, y0 + tile_h - 0.088, show(r["actual"], r["unit"], r["kpi_id"]), fontsize=24,
                 weight="bold", color=C.INK, va="top")
        fig.text(x0 + pad, y0 + tile_h - 0.158,
                 f"Plan {show(r['plan'], r['unit'], r['kpi_id'])} · {r['pct_of_plan'] * 100:.1f}% of plan",
                 fontsize=9.5, color=C.INK_2, va="top")
        # Status pill: tint, icon in the status colour, word in ink
        pill_w, pill_h = 0.085, 0.036
        px, py = x0 + tile_w - pad - pill_w, y0 + tile_h - 0.125 - pill_h / 2
        fig.patches.append(FancyBboxPatch((px, py), pill_w, pill_h, boxstyle="round,pad=0,rounding_size=0.01",
                                          transform=fig.transFigure, facecolor=STATUS_TINT[r["status"]],
                                          edgecolor="none", zorder=-1))
        fig.text(px + 0.012, py + pill_h / 2, C.STATUS_ICON[r["status"]], color=C.STATUS[r["status"]],
                 fontsize=10, va="center", ha="left")
        fig.text(px + 0.027, py + pill_h / 2, STATUS_WORD[r["status"]], color=C.INK, fontsize=9.5,
                 weight="bold", va="center", ha="left")

        # Actual against plan, over the months the KPI has a plan
        hist = sc[(sc["kpi_id"] == r["kpi_id"]) & sc["plan"].notna()]
        ax = fig.add_axes([x0 + pad + 0.006, y0 + 0.035, tile_w - 2 * pad - 0.01, tile_h * 0.36])
        ax.plot(hist["month_start"], hist["plan"], color=C.MUTED, linewidth=1.4, linestyle=(0, (4, 3)))
        ax.plot(hist["month_start"], hist["actual"], color=C.BLUE, linewidth=2)
        ax.set_facecolor("#ffffff")
        ax.set_yticks([])
        for side in ("left", "right", "top"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(C.AXIS)
        first, last = hist["month_start"].iloc[0], hist["month_start"].iloc[-1]
        ax.set_xticks([first, last])
        ax.set_xticklabels([f"{first:%b %Y}", f"{last:%b %Y}"], fontsize=8.5, color=C.INK_2)
        ax.tick_params(length=0)
        ax.set_xlim(first - pd.Timedelta(days=10), last + pd.Timedelta(days=10))
        ax.xaxis.get_majorticklabels()[0].set_horizontalalignment("left")
        ax.xaxis.get_majorticklabels()[-1].set_horizontalalignment("right")

    handles = [Line2D([], [], color=C.BLUE, linewidth=2, label="Actual"),
               Line2D([], [], color=C.MUTED, linewidth=1.4, linestyle=(0, (4, 3)), label="Plan")]
    fig.legend(handles=handles, loc="lower right", bbox_to_anchor=(0.988, 0.005), ncol=2, fontsize=9,
               labelcolor=C.INK_2, frameon=False)
    path = C.save(fig, "00_executive_scorecard.png")
    return {"title": title, "chart": path,
            "latest": [{"kpi_id": r.kpi_id, "kpi_name": r.kpi_name, "actual": round(float(r.actual), 6),
                        "plan": round(float(r.plan), 6), "status": STATUS_WORD[r.status]}
                       for r in latest.itertuples()]}
