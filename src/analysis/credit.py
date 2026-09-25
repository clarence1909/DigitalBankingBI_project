"""Analysis 4, credit: vintage curves by credit policy, roll rates, and PAR30 against the GIL ratio."""

import pandas as pd
from matplotlib.ticker import MultipleLocator

from . import common as C

POLICY_NAMES = {"v1": "v1 launch policy (Jan to Jun 2025)", "v2": "v2 growth policy (Jul to Dec 2025)",
                "v3": "v3 tightened policy (from Jan 2026)"}
POLICY_COLOURS = {"v1": C.BLUE, "v2": C.ORANGE, "v3": C.AQUA}
MAX_MOB = 12
MIN_COVERAGE = 0.5   # plot a month on book once at least half of the policy's loans have reached it


def run(con):
    curves = con.execute(f"""
        SELECT credit_policy, months_on_book,
               sum(loans) AS loans, sum(ever_30plus_loans) AS ever_30plus
        FROM kpi.vintage_curves
        WHERE months_on_book BETWEEN 0 AND {MAX_MOB}
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    curves["rate"] = curves["ever_30plus"] / curves["loans"]
    total = curves[curves["months_on_book"] == 0].set_index("credit_policy")["loans"]
    curves["coverage"] = curves["loans"] / curves["credit_policy"].map(total)
    curves = curves[curves["months_on_book"] >= 1]
    at6 = curves[curves["months_on_book"] == 6].set_index("credit_policy")["rate"]
    vintages_at6 = con.execute("""
        SELECT credit_policy, count(DISTINCT vintage_month) AS n
        FROM kpi.vintage_curves WHERE months_on_book = 6 GROUP BY 1
    """).df().set_index("credit_policy")["n"]

    roll = con.execute("""
        SELECT from_bucket, to_bucket, sum(loans) AS loans
        FROM kpi.roll_rates WHERE month_start >= DATE '2026-03-01'
        GROUP BY 1, 2
    """).df()
    totals = roll.groupby("from_bucket")["loans"].sum()

    def roll_rate(frm, to):
        return float(roll[(roll.from_bucket == frm) & (roll.to_bucket == to)]["loans"].sum() / totals[frm])

    cure_30 = roll_rate("30-59", "Current")
    forward_30 = roll_rate("30-59", "60-90")
    forward_60 = roll_rate("60-90", "90+")
    cm = con.execute("""
        SELECT c.month_start, c.par30, c.gil_ratio, c.gross_loans, p.plan_value AS par30_plan
        FROM kpi.credit_monthly AS c
        LEFT JOIN reference.plan_targets AS p ON p.kpi_id = 'K19' AND p.month_start = c.month_start
        WHERE c.gross_loans IS NOT NULL ORDER BY 1
    """).df()
    cm["month_start"] = pd.to_datetime(cm["month_start"])
    peak = cm.loc[cm["par30"].idxmax()]
    latest = cm.iloc[-1]
    gil_peak = cm.loc[cm["gil_ratio"].idxmax()]

    # Chart: cumulative share of loans ever 30+ days past due, by month on book and policy
    fig, ax = C.new_figure(height=5.4)
    fig.subplots_adjust(left=0.08, right=0.72, bottom=0.13)
    for policy in ["v1", "v2", "v3"]:
        c = curves[(curves.credit_policy == policy) & (curves.coverage >= MIN_COVERAGE)]
        ax.plot(c["months_on_book"], c["rate"], color=POLICY_COLOURS[policy], marker="o", markersize=7,
                markeredgecolor=C.SURFACE, markeredgewidth=2, label=POLICY_NAMES[policy])
        end = c.iloc[-1]
        ax.text(end["months_on_book"] + 0.25, end["rate"],
                f"{policy}: {C.pct(end['rate'])} by month {int(end['months_on_book'])}",
                va="center", fontsize=9.5, color=C.INK, weight="bold" if policy == "v2" else "normal")
    ax.set_xlim(0.5, MAX_MOB + 0.5)
    ax.set_xticks(range(1, MAX_MOB + 1))
    ax.set_xlabel("Months since the loan was paid out")
    ax.set_ylim(0, None)
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("Share of loans ever 30+ days past due")
    C.style_axis(ax)
    ax.legend(loc="upper left", fontsize=9.5, labelcolor=C.INK_2)
    ratio = at6["v2"] / at6["v1"]
    title = (f"Loans approved under the loosened v2 policy were {ratio:.1f} times as likely to be 30+ days "
             f"past due by month 6 ({C.pct(at6['v2'])} against {C.pct(at6['v1'])})")
    C.titles(fig, title, "Personal financing vintage curves, pooled by the credit policy that approved them. "
                         "Each curve runs to the month at least half of that policy's loans have reached.")
    path = C.save(fig, "04_credit_vintages_by_policy.png")

    plan = latest["par30_plan"]
    plan_note = (f"just inside the {C.pct(plan, 1)} plan" if latest["par30"] <= plan
                 else f"still above the {C.pct(plan, 1)} plan")
    if latest["gil_ratio"] >= 0.9 * gil_peak["gil_ratio"]:
        gil_note = (f"the GIL ratio (loans more than 90 days past due) has not turned yet: "
                    f"{C.pct(latest['gil_ratio'], 2)}, close to its {gil_peak['month_start']:%B %Y} peak, because "
                    f"loans that fell behind earlier are still reaching 90 days.")
    else:
        gil_note = (f"the GIL ratio (loans more than 90 days past due) is {C.pct(latest['gil_ratio'], 2)}, down from "
                    f"{C.pct(gil_peak['gil_ratio'], 2)} in {gil_peak['month_start']:%B %Y}.")
    numbers = {
        "ever_30plus_mob6": {k: round(float(v), 4) for k, v in at6.items()},
        "v2_to_v1_ratio_mob6": round(float(ratio), 2),
        "roll_30_59_to_60_90": round(forward_30, 4),
        "roll_60_90_to_90plus": round(forward_60, 4),
        "cure_30_59_to_current": round(cure_30, 4),
        "par30_peak": round(float(peak["par30"]), 4), "par30_peak_month": f"{peak['month_start']:%Y-%m}",
        "par30_latest": round(float(latest["par30"]), 4), "par30_plan_latest": round(float(plan), 4),
        "gil_latest": round(float(latest["gil_ratio"]), 4),
        "gil_peak": round(float(gil_peak["gil_ratio"]), 4), "gil_peak_month": f"{gil_peak['month_start']:%Y-%m}",
        "gross_loans_latest": round(float(latest["gross_loans"]), 2),
    }
    finding = [
        f"By month 6 on book, {C.pct(at6['v2'])} of loans approved under the v2 growth policy had been 30+ days "
        f"past due, against {C.pct(at6['v1'])} under v1 and {C.pct(at6['v3'])} for the first "
        f"{C.number_word(int(vintages_at6['v3']))} monthly vintages under the tightened v3.",
        f"Arrears roll forward rather than cure: over the last six months {C.pct(forward_30, 0)} of loans 30 to 59 "
        f"days past due were 60 to 90 days past due a month later and {C.pct(forward_60, 0)} of those went on to "
        f"90+, while only {C.pct(cure_30, 0)} cured.",
        f"PAR30 peaked at {C.pct(peak['par30'], 2)} in {peak['month_start']:%B %Y} and has eased to "
        f"{C.pct(latest['par30'], 2)} in {latest['month_start']:%B %Y} ({plan_note}) as v2 loans season and "
        f"fewer are approved; {gil_note}",
    ]
    return {"id": "credit", "title": title, "chart": path, "finding": finding, "numbers": numbers}
