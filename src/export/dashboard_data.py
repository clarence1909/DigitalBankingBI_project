"""One tall table behind the generated Power BI report.

`dashboards/extracts/dashboard_data.csv` holds the rows of every chart in the
report. Power Query in the report's model reads it once and splits it into one
table per chart on the `chart` column, so the numbers are worked out here, in
SQL and Python where the checks can see them, and the model only adds them up.

Columns
  chart        which chart the row belongs to, e.g. trend_K13 or funnel_ab
  month        month start, for charts over time
  category     row label: a KPI, channel, sign-up step, segment, category, bucket
  series       colour: Actual, Plan or Target, a channel, a flow, a policy
  x            numeric x-axis where there is one (months on book)
  count        customers, applicants and other counts
  rate         shares and rates, as fractions (0.25 is 25%), shown as percentages
  rm_millions  large money amounts, in RM millions
  rm           small money amounts, in RM
  number       other numbers (transactions per customer)
  label, detail text: the scorecard's actual and plan, as shown; each KPI's
               definition (trends); each segment's action and owner (segments)
  status, status_text   the scorecard's status, and its icon and word
  sort         display order for categories
"""

import pandas as pd

from src.config import EXTRACTS_DIR

DATA = EXTRACTS_DIR / "dashboard_data.csv"
COLUMNS = ["chart", "month", "category", "series", "x", "count", "rate", "rm_millions", "rm", "number",
           "label", "detail", "status", "status_text", "sort"]
MEASURES = ["count", "rate", "rm_millions", "rm", "number"]

# Which measure column each KPI is shown in, by its unit and size
KPI_MEASURE = {
    "K01": "count", "K02": "count", "K03": "rate", "K04": "rate", "K05": "rm", "K06": "rate",
    "K07": "count", "K08": "rate", "K09": "number", "K10": "rate", "K11": "rm_millions",
    "K12": "rate", "K13": "rm_millions", "K14": "rate", "K15": "rate", "K16": "rate",
    "K17": "rm_millions", "K18": "rm_millions", "K19": "rate", "K20": "rate", "K21": "rate",
    "K22": "rm",
}
SCALE = {"count": 1, "rate": 1, "rm_millions": 1e-6, "rm": 1, "number": 1}
STATUS_WORD = {"GREEN": "On plan", "AMBER": "Watch", "RED": "Off plan"}
STATUS_ICON = {"GREEN": "▲", "AMBER": "●", "RED": "▼"}
# Arrears buckets in the order they are shown, from the warehouse's labels to the dashboard's
BUCKETS = {"Current": "Current", "1-29": "1-29 days", "30-59": "30-59 days", "60-90": "60-90 days",
           "90+": "90+ days", "Settled": "Settled", "Written off": "Written off"}
POLICY = {"v1": "v1 launch policy", "v2": "v2 growth policy", "v3": "v3 tightened policy"}
SHORT_CHANNEL = {"organic": "Organic", "google_search": "Google Search", "meta_ads": "Meta", "tiktok": "TikTok",
                 "referral": "Refer a friend", "affiliate": "Cashback affiliates"}
LAST_OBSERVED_COHORT = "2026-05-01"   # the last cohort whose third month is in the data
RECENT_FROM = "2026-03-01"            # "last six months" for card categories and roll rates


def show(value, unit, kpi_id):
    if unit == "count":
        return f"{value:,.0f}"
    if unit == "pct":
        return f"{value * 100:.2f}%" if kpi_id in ("K15", "K19") else f"{value * 100:.1f}%"
    return f"RM{value / 1e6:,.1f}m"


def rows(frame, chart, **fixed):
    frame = frame.copy()
    frame["chart"] = chart
    for key, value in fixed.items():
        frame[key] = value
    return frame


def tiles(con):
    sc = con.execute("""
        SELECT kpi_id, kpi_name, unit, actual, plan, pct_of_plan, status
        FROM kpi.scorecard WHERE month_start = (SELECT max(month_start) FROM kpi.scorecard)
        ORDER BY kpi_id
    """).df()
    sc["category"] = sc["kpi_name"]
    sc["label"] = [show(r.actual, r.unit, r.kpi_id) for r in sc.itertuples()]
    sc["detail"] = [show(r.plan, r.unit, r.kpi_id) for r in sc.itertuples()]
    sc["rate"] = sc["pct_of_plan"].astype(float)
    sc["status_text"] = [f"{STATUS_ICON[s]} {STATUS_WORD[s]}" for s in sc["status"]]
    sc["status"] = sc["status"].map(STATUS_WORD)
    sc["sort"] = range(1, len(sc) + 1)
    return rows(sc[["category", "label", "detail", "rate", "status", "status_text", "sort"]], "tiles")


def trends(con):
    kpi = con.execute("""
        SELECT m.kpi_id, m.kpi_name, m.month_start AS month, m.value, s.plan, c.target, c.definition
        FROM kpi.kpi_monthly AS m
        JOIN reference.kpi_catalog AS c USING (kpi_id)
        LEFT JOIN kpi.scorecard AS s ON s.kpi_id = m.kpi_id AND s.month_start = m.month_start
        ORDER BY m.kpi_id, m.month_start
    """).df()
    out = []
    for kpi_id, g in kpi.groupby("kpi_id"):
        measure = KPI_MEASURE[kpi_id]
        scale = SCALE[measure]
        names = {"kpi_name": "category", "definition": "detail"}
        base = g[["month", "kpi_name", "definition"]].rename(columns=names)
        out.append(rows(base.assign(**{measure: g["value"] * scale}), f"trend_{kpi_id}", series="Actual"))
        if g["plan"].notna().any():
            p = g[g["plan"].notna()]
            out.append(rows(p[["month", "kpi_name", "definition"]].rename(columns=names)
                            .assign(**{measure: p["plan"] * scale}), f"trend_{kpi_id}", series="Plan"))
        elif g["target"].notna().any():
            out.append(rows(base.assign(**{measure: g["target"] * scale}), f"trend_{kpi_id}", series="Target"))
    return pd.concat(out, ignore_index=True)


def channel_cost(con):
    ch = con.execute(f"""
        SELECT channel, sum(spend) AS spend, sum(new_customers) AS new_customers,
               sum(m3_active_customers) AS m3_active
        FROM kpi.channel_monthly
        WHERE is_paid AND month_start <= DATE '{LAST_OBSERVED_COHORT}'
        GROUP BY 1
    """).df()
    ch["category"] = ch["channel"].map(SHORT_CHANNEL)
    per_new = ch.assign(series="Per new customer", rm=ch["spend"] / ch["new_customers"])
    per_m3 = ch.assign(series="Per customer active in month 3", rm=ch["spend"] / ch["m3_active"])
    order = per_m3.sort_values("rm")["category"].tolist()
    both = pd.concat([per_new, per_m3], ignore_index=True)
    both["sort"] = both["category"].map({c: i + 1 for i, c in enumerate(order)})
    return rows(both[["category", "series", "rm", "sort"]], "channel_cost")


def new_by_channel(con):
    df = con.execute("""
        SELECT month_start AS month, channel, new_customers AS count
        FROM kpi.channel_monthly ORDER BY 1, 2
    """).df()
    df["series"] = df["channel"].map(SHORT_CHANNEL)
    return rows(df[["month", "series", "count"]], "new_by_channel")


def funnel_ab(con):
    df = con.execute("""
        WITH f AS (SELECT * FROM marts.fct_onboarding_funnel WHERE is_in_ekyc_test)
        SELECT f.ekyc_flow, s.step_no, s.step_name,
               count(*) FILTER (WHERE f.furthest_step_no >= s.step_no) / count(*) AS rate
        FROM f CROSS JOIN reference.funnel_steps AS s
        GROUP BY ALL ORDER BY 1, 2
    """).df()
    df["category"] = df["step_name"]
    df["series"] = df["ekyc_flow"].str.capitalize()
    df["sort"] = df["step_no"]
    return rows(df[["category", "series", "rate", "sort"]], "funnel_ab")


def card_categories(con):
    df = con.execute(f"""
        SELECT merchant_category AS category, sum(spend) / 1e6 AS rm_millions
        FROM kpi.card_categories_monthly WHERE month_start >= DATE '{RECENT_FROM}'
        GROUP BY 1 ORDER BY 2 DESC
    """).df()
    df["sort"] = range(1, len(df) + 1)
    return rows(df, "card_categories")


def segments():
    seg = pd.read_csv(EXTRACTS_DIR / "customer_segments.csv")
    out = []
    for column, name in [("share_of_customers", "Customers"), ("share_of_deposits", "Deposits"),
                         ("share_of_card_spend", "Card spend")]:
        out.append(pd.DataFrame({"category": seg["segment"], "series": name, "rate": seg[column],
                                 "label": seg["action"], "detail": seg["owner"], "sort": range(1, len(seg) + 1)}))
    return rows(pd.concat(out, ignore_index=True), "segments")


def declines(con):
    df = con.execute("""
        SELECT month_start AS month, declined_insufficient_funds AS "Insufficient funds",
               declined_wrong_pin AS "Wrong PIN", declined_suspected_fraud AS "Suspected fraud"
        FROM kpi.cards_monthly ORDER BY 1
    """).df()
    long = df.melt(id_vars="month", var_name="series", value_name="count")
    return rows(long, "declines")


def deposit_mix(con):
    d = con.execute("""
        SELECT month_start AS month, casa_balance, fd_balance - promo_fd_balance AS standard_fd, promo_fd_balance
        FROM kpi.deposits_monthly ORDER BY 1
    """).df()
    out = [d[["month"]].assign(series=name, rm_millions=d[col] / 1e6)
           for col, name in [("casa_balance", "Savings (CASA)"), ("standard_fd", "Standard fixed deposits"),
                             ("promo_fd_balance", "Raya promotion deposits")]]
    return rows(pd.concat(out, ignore_index=True), "deposit_mix")


def fd_retention(con):
    df = con.execute("""
        SELECT CASE WHEN is_promo_fd THEN 'Raya promotion deposits' ELSE 'Standard fixed deposits' END AS category,
               sum(retained_30d) / sum(matured_amount) AS rate
        FROM kpi.fd_maturity_outcomes WHERE window_complete GROUP BY 1 ORDER BY 1
    """).df()
    df["rate"] = df["rate"].astype(float)
    return rows(df, "fd_retention")


def vintage(con):
    df = con.execute("""
        WITH c AS (
            SELECT credit_policy, months_on_book, sum(loans) AS loans, sum(ever_30plus_loans) AS bad
            FROM kpi.vintage_curves WHERE months_on_book BETWEEN 0 AND 12 GROUP BY 1, 2
        )
        SELECT c.credit_policy, c.months_on_book AS x, c.bad / c.loans AS rate
        FROM c JOIN c AS base ON base.credit_policy = c.credit_policy AND base.months_on_book = 0
        WHERE c.months_on_book >= 1 AND c.loans >= 0.5 * base.loans
        ORDER BY 1, 2
    """).df()
    df["series"] = df["credit_policy"].map(POLICY)
    return rows(df[["series", "x", "rate"]], "vintage")


def roll_rates(con):
    df = con.execute(f"""
        SELECT from_bucket, to_bucket, sum(loans) AS loans FROM kpi.roll_rates
        WHERE month_start >= DATE '{RECENT_FROM}' GROUP BY 1, 2
    """).df()
    df["rate"] = df["loans"] / df.groupby("from_bucket")["loans"].transform("sum")
    df["category"] = df["from_bucket"].map(BUCKETS)
    df["series"] = df["to_bucket"].map(BUCKETS)
    return rows(df[["category", "series", "rate"]], "roll_rates")


def build(con):
    parts = [
        tiles(con), trends(con), channel_cost(con), new_by_channel(con), funnel_ab(con), card_categories(con),
        declines(con), segments(), deposit_mix(con), fd_retention(con), vintage(con), roll_rates(con),
    ]
    data = pd.concat(parts, ignore_index=True).reindex(columns=COLUMNS)
    data["month"] = pd.to_datetime(data["month"]).dt.strftime("%Y-%m-%d")
    for column in MEASURES:
        data[column] = pd.to_numeric(data[column]).astype(float).round(6 if column == "rate" else 4)
    for column in ["x", "sort"]:
        data[column] = pd.to_numeric(data[column]).astype("Int64")
    data = data.sort_values(["chart", "month", "category", "series"], na_position="first", kind="stable")
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    data.to_csv(DATA, index=False, lineterminator="\n")
    return data
