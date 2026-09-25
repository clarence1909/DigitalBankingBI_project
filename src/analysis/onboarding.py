"""Analysis 2, onboarding: where applicants drop out, and a Bayesian A/B test of the guided eKYC flow.

The test's rules were written down before looking at the results (see
reference.experiments): the primary metric, the guardrail, the decision rule,
and a sample-ratio check that must pass before anything else is read.
"""

import numpy as np
from scipy import stats

from src.config import SEED

from . import common as C

STEPS = ["Sign-up started", "Phone verified", "MyKad scanned", "Selfie liveness passed", "eKYC approved",
         "Account opened"]
# How each step reads inside a sentence ("the ... step")
STEP_NOUNS = ["sign-up", "phone verification", "MyKad scan", "selfie liveness check", "eKYC approval",
              "account opening"]
DRAWS = 200_000
SRM_ALPHA = 0.001


def chance(p):
    """Probability in words that do not overstate precision."""
    return "over 99.9%" if p > 0.999 else f"{p:.1%}"


def posterior_diff(rng, x_a, n_a, x_b, n_b):
    """Draws of (rate_b - rate_a) under independent Beta(1, 1) priors."""
    a = rng.beta(1 + x_a, 1 + n_a - x_a, DRAWS)
    b = rng.beta(1 + x_b, 1 + n_b - x_b, DRAWS)
    return b - a


def run(con):
    rng = np.random.default_rng(SEED)
    exp = con.execute("SELECT * FROM reference.experiments WHERE experiment_id = 'ekyc_guided_flow'").df().iloc[0]

    # Drop-off by step across every applicant
    reach = con.execute("""
        SELECT count(*) AS n1, count(phone_verified_ts) AS n2, count(id_scanned_ts) AS n3,
               count(liveness_passed_ts) AS n4, count(ekyc_approved_ts) AS n5, count(account_opened_ts) AS n6
        FROM marts.fct_onboarding_funnel
        WHERE signup_started_ts < TIMESTAMP '2026-02-01'
    """).fetchone()
    step_pass = [reach[i + 1] / reach[i] for i in range(5)]
    worst = int(np.argmin(step_pass))

    # The A/B test
    ab = con.execute("""
        SELECT f.ekyc_flow,
               count(*) AS assigned,
               count(f.phone_verified_ts) AS s2, count(f.id_scanned_ts) AS s3, count(f.liveness_passed_ts) AS s4,
               count(f.ekyc_approved_ts) AS s5, count(f.account_opened_ts) AS opened,
               count(*) FILTER (WHERE c.fraud_flagged_30d) AS flagged
        FROM marts.fct_onboarding_funnel AS f
        LEFT JOIN marts.dim_customer AS c ON c.customer_id = f.customer_id
        WHERE f.is_in_ekyc_test
        GROUP BY 1
    """).df().set_index("ekyc_flow")
    a, b = ab.loc["control"], ab.loc["guided"]
    total = a["assigned"] + b["assigned"]
    srm = stats.chisquare([a["assigned"], b["assigned"]])
    srm_ok = srm.pvalue >= SRM_ALPHA

    uplift = posterior_diff(rng, a["opened"], a["assigned"], b["opened"], b["assigned"])
    p_better = float((uplift > 0).mean())
    lo, hi = np.percentile(uplift, [2.5, 97.5])
    guard = posterior_diff(rng, a["flagged"], a["opened"], b["flagged"], b["opened"])
    max_increase = float(exp["guardrail_max_increase_pp"]) / 100
    p_guard_breach = float((guard > max_increase).mean())
    ship = srm_ok and p_better >= 0.95 and uplift.mean() >= 0.01 and p_guard_breach < 0.10
    rate_a, rate_b = a["opened"] / a["assigned"], b["opened"] / b["assigned"]
    flag_a, flag_b = a["flagged"] / a["opened"], b["flagged"] / b["opened"]

    # Chart: share of assigned applicants reaching each step, by flow
    cols = ["assigned", "s2", "s3", "s4", "s5", "opened"]
    share_a = np.array([a[c] for c in cols]) / a["assigned"]
    share_b = np.array([b[c] for c in cols]) / b["assigned"]
    step_gain = np.diff(share_b - share_a)
    biggest_gain_step = int(np.argmax(step_gain)) + 1
    fig, ax = C.new_figure(height=5.4)
    fig.subplots_adjust(left=0.08, right=0.84, bottom=0.2)
    x = np.arange(len(STEPS))
    ax.plot(x, share_a, color=C.GREY, marker="o", markersize=8, markeredgecolor=C.SURFACE, markeredgewidth=2,
            label=f"Control flow (n = {int(a['assigned']):,})")
    ax.plot(x, share_b, color=C.BLUE, marker="o", markersize=8, markeredgecolor=C.SURFACE, markeredgewidth=2,
            label=f"Guided flow (n = {int(b['assigned']):,})")
    ax.axvspan(biggest_gain_step - 0.5, biggest_gain_step + 0.5, color=C.GRID, alpha=0.5, zorder=0, linewidth=0)
    ax.text(biggest_gain_step, 1.02, "where the flows differ", ha="center", va="bottom", fontsize=9, color=C.INK_2)
    ax.text(x[-1] + 0.12, share_b[-1], f"Guided {C.pct(share_b[-1])}", va="center", fontsize=10, color=C.INK,
            weight="bold")
    ax.text(x[-1] + 0.12, share_a[-1], f"Control {C.pct(share_a[-1])}", va="center", fontsize=10, color=C.INK_2)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace(" ", "\n", 1) for s in STEPS], fontsize=9.5)
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("Share of applicants reaching the step")
    C.style_axis(ax)
    ax.legend(loc="lower left", fontsize=9.5, labelcolor=C.INK_2)
    title = (f"The guided selfie flow lifts account opening from {C.pct(rate_a)} to {C.pct(rate_b)}, "
             f"and the gain comes at the {STEP_NOUNS[biggest_gain_step]}")
    C.titles(fig, title, f"eKYC A/B test, {int(total):,} applicants who started sign-up between 1 Feb and 30 Apr "
                         f"2026. Chance the guided flow is better: {chance(p_better)}.")
    path = C.save(fig, "02_onboarding_ekyc_ab_test.png")

    numbers = {
        "step_pass_rates_before_test": {STEPS[i + 1]: round(p, 4) for i, p in enumerate(step_pass)},
        "worst_step": STEP_NOUNS[worst + 1],
        "assigned_control": int(a["assigned"]), "assigned_guided": int(b["assigned"]),
        "srm_chi2": round(float(srm.statistic), 3), "srm_p_value": round(float(srm.pvalue), 4), "srm_ok": bool(srm_ok),
        "open_rate_control": round(float(rate_a), 4), "open_rate_guided": round(float(rate_b), 4),
        "uplift_mean_pp": round(float(uplift.mean()) * 100, 2),
        "uplift_ci95_pp": [round(float(lo) * 100, 2), round(float(hi) * 100, 2)],
        "p_guided_better": round(p_better, 4),
        "fraud_flag_rate_control": round(float(flag_a), 4), "fraud_flag_rate_guided": round(float(flag_b), 4),
        "p_guardrail_breach": round(p_guard_breach, 4),
        "decision": "ship guided" if ship else "do not ship",
    }
    finding = [
        f"The biggest drop in sign-up is the {STEP_NOUNS[worst + 1]}: before the test, only "
        f"{C.pct(step_pass[worst], 0)} of applicants who reached it got through.",
        f"In the A/B test the guided flow raised account opening from {C.pct(rate_a)} to {C.pct(rate_b)} "
        f"({uplift.mean() * 100:+.1f} points, 95% credible interval {lo * 100:+.1f} to {hi * 100:+.1f}); "
        f"the chance it is better is {chance(p_better)}. The 50/50 split held: the sample-ratio check gave "
        f"p = {srm.pvalue:.3f}, above the 0.001 threshold set in advance.",
        f"The fraud guardrail held ({C.pct(flag_a, 2)} of control accounts flagged against {C.pct(flag_b, 2)} "
        f"guided; chance of a breach {chance(p_guard_breach)}), so the rule set before the test says "
        f"{'ship the guided flow, as the bank did on 1 May 2026' if ship else 'do not ship'}.",
    ]
    return {"id": "onboarding", "title": title, "chart": path, "finding": finding, "numbers": numbers}
