"""The insights report and the README's headline findings, written from the analysis results.

Every number comes from reports/findings.json or the warehouse, so the words
cannot fall out of step with the data: rerun the pipeline and the report,
recommendations and README update together.
"""

import re

from src.analysis import common as C
from src.analysis.segments import ACTIONS
from src.config import REPORTS_DIR, ROOT

REPORT = REPORTS_DIR / "insights_report.md"
README = ROOT / "README.md"
START, END = "<!-- findings:start -->", "<!-- findings:end -->"
CHECKS_START, CHECKS_END = "<!-- checks:start -->", "<!-- checks:end -->"


def kpi_facts(con):
    """Latest value and target for the KPIs the recommendations are measured by."""
    rows = con.execute("""
        SELECT c.kpi_id, c.kpi_name, c.target,
               arg_max(m.value, m.month_start) AS latest,
               max(m.month_start) AS latest_month
        FROM reference.kpi_catalog AS c
        LEFT JOIN kpi.kpi_monthly AS m USING (kpi_id)
        GROUP BY ALL
    """).df().set_index("kpi_id")
    plans = con.execute("""
        SELECT kpi_id, plan_value FROM reference.plan_targets
        WHERE month_start = (SELECT max(month_start) FROM reference.plan_targets)
    """).df().set_index("kpi_id")["plan_value"]
    rows["plan"] = plans
    return rows


def recommendations(f, k):
    acq, onb, dep, cred, seg = (f[x]["numbers"] for x in ("acquisition", "onboarding", "deposits", "credit",
                                                           "segments"))
    channels = acq["channels"]
    spend = sum(c["spend"] for c in channels)
    retained = sum(c["new_customers"] * c["m3_rate"] for c in channels)
    blended = spend / retained
    ranked = sorted(channels, key=lambda c: c["cost_per_m3"])
    tiktok = next(c for c in channels if c["channel"] == "tiktok")
    short = {c["channel"]: re.sub(r"\s*\(.*\)", "", c["channel_name"]) for c in channels}
    segments = {s["segment"]: s for s in seg["segments"]}
    new_money = 100 - dep["promo_pct_from_existing_savings"]

    return {
        "acquisition": {
            "recommendation": (
                f"Judge channels on the cost of a customer still active in month 3, not the cost of a sign-up, and "
                f"show both side by side in the monthly pack. Move budget from TikTok ({C.rm(tiktok['cost_per_m3'])} "
                f"per retained customer) towards {short[ranked[0]['channel']]} ({C.rm(ranked[0]['cost_per_m3'])}) and "
                f"{short[ranked[1]['channel']]} ({C.rm(ranked[1]['cost_per_m3'])}). Build card activation into every "
                f"channel's first week: {C.pct(acq['m3_rate_card_activated_30d'], 0)} of customers who activate "
                f"their card within 30 days are still active in month 3, against "
                f"{C.pct(acq['m3_rate_card_not_activated_30d'], 0)} of those who do not."),
            "owner": "Head of Growth, with the Head of Cards for card activation",
            "measure": (
                f"Blended cost per month-3-active customer across paid channels falls from {C.rm(blended)} to "
                f"{C.rm(blended * 0.8)} within two quarters while new customers (K02) stay on plan, and card "
                f"activation within 30 days (K10) rises from {C.pct(k.loc['K10', 'latest'], 0)} towards its "
                f"{C.pct(k.loc['K10', 'target'], 0)} target."),
        },
        "onboarding": {
            "recommendation": (
                "Keep the guided selfie flow for every applicant (it went live on 1 May 2026), and aim the next "
                f"test at the same step, since the {onb['worst_step']} is still where most applicants are lost. "
                "Reuse the rules that made this test trustworthy: a sample-ratio check before anything else, a "
                "fraud guardrail, and a decision rule written down before the results are read."),
            "owner": "Head of Onboarding",
            "measure": (
                f"eKYC completion (K04) stays at or above its {C.pct(k.loc['K04', 'target'], 0)} target (it was "
                f"{C.pct(k.loc['K04', 'latest'])} in August 2026), onboarding conversion (K03) reaches "
                f"{C.pct(k.loc['K03', 'target'], 0)} (now {C.pct(k.loc['K03', 'latest'])}), and the share of new "
                f"accounts flagged for fraud within 30 days does not rise by more than half a point."),
        },
        "deposits": {
            "recommendation": (
                "Price the next promotion for new money only: pay the promotional rate on balances above what the "
                "customer already holds at Kelip, cap the campaign's size, and treat the CASA ratio's amber band as "
                "a stop-loss. Contact promotion customers two weeks before maturity with a rollover offer."),
            "owner": "Treasurer",
            "measure": (
                f"In the next promotion at least half of the money placed is new to Kelip (against "
                f"{new_money:.0f}% for Raya 2025), the CASA ratio (K14) stays within its amber band of the "
                f"{C.pct(k.loc['K14', 'plan'], 0)} plan, and at least {C.pct(k.loc['K16', 'target'], 0)} of "
                f"promotion money is still with the bank 30 days after maturity (K16; Raya 2025 kept "
                f"{C.pct(dep['promo_retention_30d'], 0)})."),
        },
        "credit": {
            "recommendation": (
                "Keep the tightened v3 policy, and reopen grade D or debt service ratios above 45% only as a capped "
                "pilot with its own vintage tracking. Add an early-warning trigger when a vintage's share of loans "
                "30+ days past due runs above the v1 curve, and move collections effort to loans 30 to 59 days past "
                f"due, where only {C.pct(cred['cure_30_59_to_current'], 0)} cure."),
            "owner": "Head of Credit Risk",
            "measure": (
                f"Early delinquency at month 6 (K21) stays below its {C.pct(k.loc['K21', 'target'], 0)} target for "
                f"every v3 vintage, PAR30 (K19) stays at or below the {C.pct(k.loc['K19', 'plan'], 1)} plan, and "
                f"the cure rate from 30 to 59 days past due rises from {C.pct(cred['cure_30_59_to_current'], 0)} "
                f"to 35%."),
        },
        "segments": {
            "recommendation": "Run one play per segment, each with its own owner.",
            "plays": [f"**{name}** ({C.pct(segments[name]['share_of_customers'], 0)} of customers, "
                      f"{C.pct(segments[name]['share_of_deposits'], 0)} of deposits): {action} Owner: {owner}."
                      for name, (action, owner) in ACTIONS.items() if name in segments],
            "owner": "Head of Product, with the segment owners named above",
            "measure": (
                f"The dormant share of customers falls from {C.pct(segments['Dormant']['share_of_customers'], 0)} to "
                f"below 20% within two quarters, the active customer rate (K08) rises from "
                f"{C.pct(k.loc['K08', 'latest'], 0)} towards its {C.pct(k.loc['K08', 'target'], 0)} target, and "
                f"savers keep their {C.pct(segments['Savers']['share_of_deposits'], 0)} share of deposits through "
                f"the next rate change."),
        },
    }


SECTIONS = [
    ("acquisition", "Acquisition", "Cohorts that opened from September 2024 to May 2026 (the last cohort with a "
     "third month in the data); paid channels only. Spend is the cleaned marketing sheet; a customer is active in "
     "month 3 if they made a transaction themselves in the third month after opening.",
     ["../src/analysis/acquisition.py", "../sql/03_kpi/01_kpi_growth.sql",
      "../sql/adhoc/01_cost_per_retained_customer_by_channel.sql"]),
    ("onboarding", "Onboarding", "Funnel steps from the app events. The A/B test is Bayesian: Beta(1, 1) priors "
     "and 200,000 draws from each posterior. The sample-ratio check (chi-square, p of at least 0.001), the fraud "
     "guardrail (flagged within 30 days, breached if the guided flow is worse by more than 0.5 points) and the "
     "decision rule were fixed in reference.experiments before the results were read.",
     ["../src/analysis/onboarding.py", "../data/reference/experiments.csv", "../sql/adhoc/05_onboarding_time_by_flow.sql"]),
    ("deposits", "Deposits", "Month-end balances and ledger postings. Money counts as new to Kelip when it was "
     "transferred into the customer's savings in the three hours before the promotion placement; retention is "
     "measured 30 days after each deposit matured.",
     ["../src/analysis/deposits.py", "../sql/03_kpi/04_kpi_deposits.sql", "../sql/adhoc/02_raya_promo_funding.sql"]),
    ("credit", "Credit", "Vintage curves pooled by the credit policy that approved each loan; each curve runs to "
     "the month at least half of that policy's loans have reached. Roll rates cover March to August 2026.",
     ["../src/analysis/credit.py", "../sql/03_kpi/05_kpi_credit.sql", "../sql/adhoc/04_vintages_above_appetite.sql"]),
    ("segments", "Customer segments", "k-means on four behaviour features (average balance and card purchases, "
     "both logged, card share of spending, share of months active), standardised, with k from 2 to 8 chosen by "
     "silhouette score. Customers who opened by February 2026, behaviour from March to August 2026; customers with "
     "no transactions of their own are dormant by rule.",
     ["../src/analysis/segments.py", "../sql/02_marts/12_fct_customer_monthly.sql",
      "../dashboards/extracts/customer_segments.csv"]),
]


def link(path):
    return f"[`{path.replace('../', '')}`]({path})"


def write_report(findings, executive, recs):
    lines = [
        "# Kelip Bank insights report, August 2026",
        "",
        "<!-- Generated by src/report.py from reports/findings.json and the warehouse. Rerun the pipeline to "
        "update it. -->",
        "",
        "> **All data is synthetic.** Kelip Bank is a fictional Malaysian digital bank. The simulator plants "
        "five stories with known answers, so these findings show the methods working, not facts about any "
        "real bank.",
        "",
        f"**Scorecard:** {executive['title']}.",
        "",
        "![Executive scorecard: six KPIs against plan for August 2026](charts/00_executive_scorecard.png)",
        "",
        "## Summary",
        "",
        "| # | Finding | Recommendation | Owner |",
        "|---|---|---|---|",
    ]
    for i, (key, *_rest) in enumerate(SECTIONS, start=1):
        first_sentence = recs[key]["recommendation"].split(". ")[0].rstrip(".") + "."
        lines.append(f"| {i} | {findings[key]['title']} | {first_sentence} | {recs[key]['owner']} |")
    for i, (key, name, method, sources) in enumerate(SECTIONS, start=1):
        f, r = findings[key], recs[key]
        lines += ["", f"## {i}. {name}: {f['title']}", "",
                  f"![{f['title']}]({f['chart'].removeprefix('reports/')})", "", "**Evidence**", ""]
        lines += [f"- {line}" for line in f["finding"]]
        lines += ["", f"**Recommendation.** {r['recommendation']}", ""]
        if r.get("plays"):
            lines += [f"- {play}" for play in r["plays"]] + [""]
        lines += [f"**Owner.** {r['owner']}", "",
                  f"**Measure of success.** {r['measure']}", "",
                  f"**How it was found.** {method} Code and SQL: {', '.join(link(s) for s in sources)}."]
    lines += [
        "", "## Limits of these findings", "",
        "- The data is simulated. The stories were planted on purpose, so the value here is in the methods, "
        "which recover known answers, rather than in the numbers themselves.",
        "- Channel costs come from a hand-kept spreadsheet. August 2026's Meta invoice is missing, so August "
        "has no cost per new customer, and the January 2026 total has a typing error the checks flag.",
        "- Month-3 activity, fixed deposit retention and early delinquency need time to observe, so the "
        "latest cohorts drop out of those measures until their window closes.",
        "- The segments describe behaviour, not value or profitability; a bank would add product holdings "
        "and revenue before targeting offers.",
        "",
        "See also: [data quality report](data_quality_report.md), [Excel pack check](excel_pack_check.md), "
        "[KPI dictionary](../docs/05_kpi_dictionary.md).",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def replace_block(text, start, end, lines):
    if start in text and end in text:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: "\n".join([start, ""] + lines + ["", end]),
                      text, flags=re.S)
    return text


def checks_block(con, excel_summary):
    counts = dict(con.execute("SELECT status, count(*) FROM dq.check_results GROUP BY 1").fetchall())
    total = sum(counts.values())
    recon = con.execute("""
        SELECT (SELECT count(*) FROM dq.recon_deposits_monthly WHERE difference <> 0),
               (SELECT count(*) FROM dq.recon_cards_monthly WHERE difference <> 0),
               (SELECT count(*) FROM dq.recon_deposits_monthly)
    """).fetchone()
    lines = [
        f"- **{total} data quality checks** on every build: {counts.get('PASS', 0)} pass, "
        f"{counts.get('WARN', 0)} warn about problems planted in the marketing spreadsheet (a missing invoice and a "
        f"typing error in its total), {counts.get('INFO', 0)} report numbers for information, "
        f"{counts.get('FAIL', 0)} fail ([report](reports/data_quality_report.md)).",
        (f"- **Both reconciliations tie to the sen in all {recon[2]} months:** ledger postings to month-end "
         f"balances, account by account, and the card processor's settlements to the ledger."
         if recon[0] == 0 and recon[1] == 0 else
         f"- **Reconciliations:** {recon[0]} of {recon[2]} months differ between ledger postings and month-end "
         f"balances, and {recon[1]} between the card processor and the ledger."),
    ]
    if excel_summary:
        facts = dict(excel_summary)
        lines.append(f"- **The Excel pack recalculates cleanly:** {facts['Formulas recalculated']} formulas, "
                     f"{facts['Cells with an error value']} errors, and its values match the warehouse "
                     f"([check](reports/excel_pack_check.md)).")
    lines += [
        "- **Every error and warning check is proved to work** by breaking the data on purpose "
        "([break-tests](reports/break_test_report.md)).",
        "- **Two clean runs give identical files**, checked in CI on every push.",
    ]
    return lines


def update_readme(findings, con=None, excel_summary=None):
    picks = [("acquisition", 0), ("deposits", 0), ("credit", 1)]
    block = [START, "", "From the [insights report](reports/insights_report.md), which has five findings, each "
             "with a recommendation, an owner and a measure of success:", ""]
    for i, (key, line) in enumerate(picks, start=1):
        block.append(f"{i}. **{findings[key]['title']}.** {findings[key]['finding'][line]}")
    text = README.read_text(encoding="utf-8")
    text = replace_block(text, START, END, block[2:])
    if con is not None:
        text = replace_block(text, CHECKS_START, CHECKS_END, checks_block(con, excel_summary))
    README.write_text(text, encoding="utf-8")


def write(con, findings, executive, excel_summary=None):
    recs = recommendations(findings, kpi_facts(con))
    write_report(findings, executive, recs)
    update_readme(findings, con, excel_summary)
    return REPORT
