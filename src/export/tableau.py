"""Tidy CSV extracts for the dashboard.

One file per dashboard need, in long (tidy) form where that helps, so Tableau,
Power BI or Qlik can read them as they are. They are small and committed to
the repo, which is also what Tableau Public connects to.
"""

from src.config import EXTRACTS_DIR

# The status icon travels with the status word, so no page shows status by colour alone
ICON = "CASE status WHEN 'GREEN' THEN '▲' WHEN 'AMBER' THEN '●' WHEN 'RED' THEN '▼' END"

EXTRACTS = {
    "kpi_catalog": """
        SELECT kpi_id, kpi_name, family, definition, formula, owner, unit, direction, amber_tolerance,
               target, target_note, is_scorecard, dashboard_page
        FROM reference.kpi_catalog ORDER BY kpi_id""",
    "kpi_monthly": f"""
        SELECT m.month_start, m.kpi_id, m.kpi_name, m.family, m.unit, m.direction, m.value,
               s.plan, s.status, s.status_label, {ICON.replace('status', 's.status')} AS status_icon
        FROM kpi.kpi_monthly AS m
        LEFT JOIN kpi.scorecard AS s ON s.kpi_id = m.kpi_id AND s.month_start = m.month_start
        ORDER BY m.kpi_id, m.month_start""",
    "scorecard": f"SELECT *, {ICON} AS status_icon FROM kpi.scorecard ORDER BY month_start, kpi_id",
    "growth_channels": "SELECT * FROM kpi.channel_monthly ORDER BY month_start, channel",
    "onboarding_funnel": """
        WITH f AS (SELECT * FROM marts.fct_onboarding_funnel)
        SELECT start_month, ekyc_flow, is_in_ekyc_test, s.step_no, s.step_name,
               count(*) FILTER (WHERE f.furthest_step_no >= s.step_no) AS applicants
        FROM f CROSS JOIN reference.funnel_steps AS s
        GROUP BY ALL
        ORDER BY start_month, ekyc_flow, is_in_ekyc_test, step_no""",
    "engagement_monthly": "SELECT * FROM kpi.engagement_monthly ORDER BY month_start",
    "cards_monthly": "SELECT * FROM kpi.cards_monthly ORDER BY month_start",
    "card_categories_monthly": "SELECT * FROM kpi.card_categories_monthly ORDER BY month_start, spend DESC",
    "deposits_monthly": "SELECT * FROM kpi.deposits_monthly ORDER BY month_start",
    "fd_maturity_outcomes": """
        SELECT maturity_month, is_promo_fd, count(*) AS deposits_matured,
               sum(matured_amount) AS matured_amount,
               sum(matured_amount) FILTER (WHERE rolled_over) AS rolled_over_amount,
               sum(left_within_30d) AS left_within_30d, sum(retained_30d) AS retained_30d,
               bool_and(window_complete) AS window_complete
        FROM kpi.fd_maturity_outcomes
        GROUP BY 1, 2 ORDER BY 1, 2""",
    "credit_monthly": "SELECT * FROM kpi.credit_monthly ORDER BY month_start",
    "vintage_curves": "SELECT * FROM kpi.vintage_curves ORDER BY vintage_month, months_on_book",
    "roll_rates": "SELECT * FROM kpi.roll_rates ORDER BY month_start, from_bucket, to_bucket",
    "finance_monthly": "SELECT * FROM kpi.finance_monthly ORDER BY month_start",
}


def export(con):
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name, sql in EXTRACTS.items():
        df = con.execute(sql).df()
        path = EXTRACTS_DIR / f"{name}.csv"
        df.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")
        written.append((path, len(df)))
    return written
