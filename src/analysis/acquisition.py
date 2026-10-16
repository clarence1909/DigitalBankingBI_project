"""Analysis 1, acquisition: what a sign-up costs against what a customer who stays costs.

Cohorts that opened from Sep 2024 to May 2026 (the last cohort whose third
month is inside the data), paid channels only.
"""

from . import common as C

LAST_OBSERVED_COHORT = "2026-05-01"


def run(con):
    ch = con.execute(f"""
        SELECT channel, channel_name, is_paid,
               sum(new_customers) AS new_customers,
               sum(spend) AS spend,
               sum(m3_active_customers) AS m3_active
        FROM kpi.channel_monthly
        WHERE month_start <= DATE '{LAST_OBSERVED_COHORT}'
        GROUP BY ALL
    """).df()
    ch["m3_rate"] = ch["m3_active"] / ch["new_customers"]
    paid = ch[ch["is_paid"]].copy()
    paid["cost_per_new"] = paid["spend"] / paid["new_customers"]
    paid["cost_per_m3"] = paid["spend"] / paid["m3_active"]
    overall_m3 = ch["m3_active"].sum() / ch["new_customers"].sum()

    cheapest = paid.loc[paid["cost_per_new"].idxmin()]
    priciest = paid.loc[paid["cost_per_m3"].idxmax()]
    best = paid.loc[paid["cost_per_m3"].idxmin()]

    # Story 5 evidence: early card activation and staying active, within the same channel
    card = con.execute(f"""
        SELECT c.card_activated_30d,
               avg(CASE WHEN a.is_active THEN 1.0 ELSE 0.0 END) AS m3_rate,
               count(*) AS customers
        FROM marts.dim_customer AS c
        LEFT JOIN marts.fct_customer_monthly AS a ON a.customer_id = c.customer_id AND a.months_since_open = 3
        WHERE c.has_debit_card AND c.cohort_month <= DATE '{LAST_OBSERVED_COHORT}'
          AND c.acquisition_channel NOT IN ('tiktok', 'affiliate')
        GROUP BY 1
    """).df().set_index("card_activated_30d")

    # Chart: a dumbbell per paid channel, cost per sign-up to cost per month-3-active customer
    order = paid.sort_values("cost_per_m3", ascending=True).reset_index(drop=True)
    fig, ax = C.new_figure(height=5.4)
    fig.subplots_adjust(left=0.24, right=0.95, bottom=0.12)
    y = range(len(order))
    for i, r in order.iterrows():
        ax.plot([r["cost_per_new"], r["cost_per_m3"]], [i, i], color=C.GREY, linewidth=2.4, zorder=1)
    ax.scatter(order["cost_per_new"], y, s=110, color=C.BLUE_LIGHT, edgecolor=C.SURFACE, linewidth=2,
               zorder=3, label="Cost per new customer")
    ax.scatter(order["cost_per_m3"], y, s=110, color=C.BLUE, edgecolor=C.SURFACE, linewidth=2,
               zorder=3, label="Cost per customer still active in month 3")
    for i, r in order.iterrows():
        ax.text(r["cost_per_new"] - 2.2, i, C.rm(r["cost_per_new"]), ha="right", va="center", fontsize=9.5,
                color=C.INK_2)
        ax.text(r["cost_per_m3"] + 2.2, i, C.rm(r["cost_per_m3"]), ha="left", va="center", fontsize=9.5,
                color=C.INK, weight="bold" if r["channel"] == priciest["channel"] else "normal")
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{r['channel_name']}\n{C.pct(r['m3_rate'], 0)} active in month 3"
                        for _, r in order.iterrows()], fontsize=9.5)
    for lbl, (_, r) in zip(ax.get_yticklabels(), order.iterrows()):
        if r["channel"] == priciest["channel"]:
            lbl.set_weight("bold")
            lbl.set_color(C.INK)
    ax.set_xlim(0, order["cost_per_m3"].max() * 1.18)
    ax.xaxis.set_major_formatter(lambda v, _: f"RM{v:,.0f}")
    C.style_axis(ax, grid_axis="x")
    ax.legend(loc="lower right", fontsize=9.5, labelcolor=C.INK_2)
    if cheapest["channel"] == priciest["channel"]:
        title = (f"{cheapest['channel_name']} is the cheapest channel per sign-up ({C.rm(cheapest['cost_per_new'])}) "
                 f"but the most expensive per customer who stays ({C.rm(priciest['cost_per_m3'])})")
    else:
        title = (f"{priciest['channel_name']} costs the most per customer still active in month 3 "
                 f"({C.rm(priciest['cost_per_m3'])})")
    C.titles(fig, title, "Marketing spend per account opened, and per customer still transacting three months "
                         "later. Paid channels, customers who opened Sep 2024 to May 2026.")
    path = C.save(fig, "01_acquisition_cost_per_retained_customer.png")

    m3_card = card.loc[True, "m3_rate"]
    m3_nocard = card.loc[False, "m3_rate"]
    numbers = {
        "channels": order[["channel", "channel_name", "new_customers", "spend", "cost_per_new", "m3_rate",
                           "cost_per_m3"]].round(4).to_dict(orient="records"),
        "overall_m3_rate": round(overall_m3, 4),
        "cheapest_channel": cheapest["channel_name"],
        "priciest_channel": priciest["channel_name"],
        "best_channel": best["channel_name"],
        "m3_rate_card_activated_30d": round(m3_card, 4),
        "m3_rate_card_not_activated_30d": round(m3_nocard, 4),
    }
    if cheapest["channel"] == priciest["channel"]:
        first = (f"{priciest['channel_name']} brought in {int(priciest['new_customers']):,} customers at "
                 f"{C.rm(priciest['cost_per_new'])} each, the lowest cost of any paid channel, but only "
                 f"{C.pct(priciest['m3_rate'], 0)} were still active in their third month, against "
                 f"{C.pct(overall_m3, 0)} across all channels.")
    else:
        first = (f"{cheapest['channel_name']} is the cheapest paid channel per sign-up "
                 f"({C.rm(cheapest['cost_per_new'])}); {priciest['channel_name']} keeps only "
                 f"{C.pct(priciest['m3_rate'], 0)} of its customers active to month 3, against "
                 f"{C.pct(overall_m3, 0)} across all channels.")
    finding = [
        first,
        f"Per customer still active in month 3, {priciest['channel_name']} cost {C.rm(priciest['cost_per_m3'])}, "
        f"{priciest['cost_per_m3'] / best['cost_per_m3']:.1f} times as much as {best['channel_name']} "
        f"({C.rm(best['cost_per_m3'])}).",
        f"Customers who activate their debit card within 30 days are far more likely to stay: "
        f"{C.pct(m3_card, 0)} are active in month 3 against {C.pct(m3_nocard, 0)} of those who do not "
        f"(same channels, so not just channel mix).",
    ]
    return {"id": "acquisition", "title": title, "chart": path, "finding": finding, "numbers": numbers}
