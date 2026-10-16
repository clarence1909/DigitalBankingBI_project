"""Analysis 3, deposits: what the Raya FD promotion did to CASA, cost of funds and retention."""

import matplotlib.dates as mdates
import pandas as pd

from . import common as C

PROMO_START, PROMO_END = "2025-03-01", "2025-05-01"


def run(con):
    d = con.execute("""
        SELECT d.month_start, d.casa_ratio, d.cost_of_funds, d.total_deposits, d.promo_fd_balance,
               p.plan_value AS casa_plan
        FROM kpi.deposits_monthly AS d
        LEFT JOIN reference.plan_targets AS p ON p.kpi_id = 'K14' AND p.month_start = d.month_start
        ORDER BY 1
    """).df()
    d["month_start"] = pd.to_datetime(d["month_start"])
    pre = d[d["month_start"] < PROMO_START].iloc[-1]
    after = d[d["month_start"] >= PROMO_START]
    trough = after.loc[after["casa_ratio"].idxmin()]
    peak_cof = after.loc[after["cost_of_funds"].idxmax()]
    back = after[(after["month_start"] > trough["month_start"]) & (after["casa_ratio"] >= 0.80)]
    recovered = back.iloc[0]["month_start"] if len(back) else None

    funding = con.execute(open_adhoc("02_raya_promo_funding.sql")).df().iloc[0]
    fd = con.execute("""
        SELECT is_promo_fd, sum(matured_amount) AS matured, sum(retained_30d) AS retained,
               sum(matured_amount) FILTER (WHERE rolled_over) AS rolled,
               sum(left_within_30d) AS left_bank, count(*) AS deposits
        FROM kpi.fd_maturity_outcomes WHERE window_complete GROUP BY 1
    """).df().set_index("is_promo_fd")
    promo, std = fd.loc[True], fd.loc[False]

    # Chart: two small multiples on one time axis (never a dual axis)
    fig, (ax1, ax2) = C.new_figure(nrows=2, height=6.2, sharex=True)
    fig.subplots_adjust(left=0.09, right=0.86, bottom=0.08, hspace=0.35)
    for ax in (ax1, ax2):
        ax.axvspan(pd.Timestamp(PROMO_START) - pd.Timedelta(days=15), pd.Timestamp(PROMO_END) + pd.Timedelta(days=15),
                   color=C.GRID, alpha=0.6, zorder=0, linewidth=0)
        C.style_axis(ax)
    ax1.plot(d["month_start"], d["casa_plan"], color=C.MUTED, linewidth=1.2, zorder=2)
    ax1.plot(d["month_start"], d["casa_ratio"], color=C.BLUE, zorder=3)
    ax1.scatter([trough["month_start"]], [trough["casa_ratio"]], s=70, color=C.BLUE, edgecolor=C.SURFACE,
                linewidth=2, zorder=4)
    ax1.annotate(f"{C.pct(trough['casa_ratio'], 0)} in {trough['month_start']:%b %Y}",
                 (trough["month_start"], trough["casa_ratio"]), xytext=(12, -4), textcoords="offset points",
                 fontsize=9.5, color=C.INK)
    ax1.text(pd.Timestamp("2026-01-01"), d["casa_plan"].iloc[-1] + 0.012, f"Plan {C.pct(d['casa_plan'].iloc[-1], 0)}",
             va="bottom", ha="center", fontsize=9, color=C.MUTED)
    ax1.text(d["month_start"].iloc[-1] + pd.Timedelta(days=12), d["casa_ratio"].iloc[-1],
             C.pct(d["casa_ratio"].iloc[-1], 0), va="center", fontsize=9.5, color=C.INK)
    ax1.set_ylim(0.5, 1.0)
    ax1.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax1.set_title("CASA ratio: savings as a share of all deposits", loc="left", fontsize=10.5, color=C.INK_2)
    ax1.text(pd.Timestamp("2025-04-01"), 0.99, "Raya FD promotion", ha="center", va="top", fontsize=9,
             color=C.INK_2)

    ax2.plot(d["month_start"], d["cost_of_funds"], color=C.BLUE, zorder=3)
    ax2.scatter([peak_cof["month_start"]], [peak_cof["cost_of_funds"]], s=70, color=C.BLUE, edgecolor=C.SURFACE,
                linewidth=2, zorder=4)
    ax2.annotate(f"{C.pct(peak_cof['cost_of_funds'], 2)} in {peak_cof['month_start']:%b %Y}",
                 (peak_cof["month_start"], peak_cof["cost_of_funds"]), xytext=(12, 2), textcoords="offset points",
                 fontsize=9.5, color=C.INK)
    ax2.axvline(pd.Timestamp("2025-07-09"), color=C.AXIS, linewidth=1)
    ax2.text(pd.Timestamp("2025-07-09") + pd.Timedelta(days=8), 0.0156, "OPR cut to 2.75%", fontsize=8.5,
             color=C.MUTED, va="bottom")
    ax2.text(d["month_start"].iloc[-1] + pd.Timedelta(days=12), d["cost_of_funds"].iloc[-1],
             C.pct(d["cost_of_funds"].iloc[-1], 2), va="center", fontsize=9.5, color=C.INK)
    ax2.set_ylim(0.015, 0.028)
    ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.1%}")
    ax2.set_title("Cost of funds: interest paid on deposits, annualised", loc="left", fontsize=10.5, color=C.INK_2)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))

    title = (f"The Raya FD promotion took the CASA ratio from {C.pct(pre['casa_ratio'], 0)} to "
             f"{C.pct(trough['casa_ratio'], 0)} and pushed cost of funds to {C.pct(peak_cof['cost_of_funds'], 2)}")
    C.titles(fig, title, "Month-end savings and fixed deposit balances, Sep 2024 to Aug 2026. "
                         "Grey band: 6-month FD at 3.88% a year, placed 1 Mar to 31 May 2025.", extra_top=0.1)
    path = C.save(fig, "03_deposits_fd_promotion.png")

    numbers = {
        "casa_ratio_before": round(float(pre["casa_ratio"]), 4),
        "casa_ratio_trough": round(float(trough["casa_ratio"]), 4),
        "trough_month": f"{trough['month_start']:%Y-%m}",
        "cost_of_funds_before": round(float(pre["cost_of_funds"]), 5),
        "cost_of_funds_peak": round(float(peak_cof["cost_of_funds"]), 5),
        "peak_month": f"{peak_cof['month_start']:%Y-%m}",
        "casa_back_to_80_pct": f"{recovered:%Y-%m}" if recovered is not None else None,
        "promo_placed": round(float(funding["total_placed"]), 2),
        "promo_pct_from_existing_savings": float(funding["pct_from_existing_savings"]),
        "promo_retention_30d": round(float(promo["retained"] / promo["matured"]), 4),
        "promo_rolled_over_share": round(float(promo["rolled"] / promo["matured"]), 4),
        "promo_left_bank_share": round(float(promo["left_bank"] / promo["matured"]), 4),
        "standard_retention_30d": round(float(std["retained"] / std["matured"]), 4),
    }
    finding = [
        f"Of {C.rm_m(funding['total_placed'])} placed in the promotion, {funding['pct_from_existing_savings']:.0f}% "
        f"came out of customers' own Kelip savings, so most of it repriced existing money from about 2% to 3.88% "
        f"rather than attracting new deposits.",
        f"The CASA ratio fell from {C.pct(pre['casa_ratio'], 0)} to {C.pct(trough['casa_ratio'], 0)} by "
        f"{trough['month_start']:%B %Y} and cost of funds peaked at {C.pct(peak_cof['cost_of_funds'], 2)} in "
        f"{peak_cof['month_start']:%B %Y}; the ratio only got back to 80% in "
        f"{recovered:%B %Y}." if recovered is not None else "The CASA ratio has not yet recovered to 80%.",
        f"At maturity, {C.pct(promo['retained'] / promo['matured'], 0)} of promotion money was still with the bank "
        f"30 days later ({C.pct(promo['rolled'] / promo['matured'], 0)} rolled over), against "
        f"{C.pct(std['retained'] / std['matured'], 0)} for standard fixed deposits.",
    ]
    return {"id": "deposits", "title": title, "chart": path, "finding": finding, "numbers": numbers}


def open_adhoc(name):
    from src.config import SQL_DIR
    return (SQL_DIR / "adhoc" / name).read_text(encoding="utf-8")
