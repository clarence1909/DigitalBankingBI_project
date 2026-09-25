"""Every number the simulator uses, in one place.

The simulator plants five stories with known answers, so the analysis can
prove its methods find them:

1. A cheap channel whose customers leave (TikTok: lowest cost per sign-up,
   highest cost per customer still active in month 3).
2. An eKYC drop-off at the selfie liveness step, and an A/B test of a guided
   flow that fixes part of it (Feb to Apr 2026, rolled out 1 May 2026).
3. An FD promotion that dilutes CASA (the Raya FD promo, Mar to May 2025).
4. A looser credit policy (personal financing policy v2, Jul to Dec 2025).
5. Customers who activate their debit card in the first 30 days churn less.

Rates are anchored to published Malaysian figures: the OPR was 3.00% until
Bank Negara Malaysia cut it to 2.75% on 9 July 2025, and Kelip Bank passes
the cut through to its deposit rates from 1 August 2025.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Acquisition: applicants who start sign-up, per channel per month
# (linear ramp from Sep 2024 to Aug 2026, before seasonality and noise)
# ---------------------------------------------------------------------------
CHANNELS = ["organic", "google_search", "meta_ads", "tiktok", "referral", "affiliate"]

APPLICANTS_START = {"organic": 420, "google_search": 330, "meta_ads": 380,
                    "tiktok": 260, "referral": 60, "affiliate": 150}
APPLICANTS_END = {"organic": 900, "google_search": 560, "meta_ads": 620,
                  "tiktok": 820, "referral": 380, "affiliate": 330}

# Extra demand in campaign months (11.11 and 12.12 sales, Raya, New Year)
SEASONALITY = {"2024-11": 1.12, "2024-12": 1.12, "2025-01": 1.05, "2025-03": 1.10,
               "2025-11": 1.12, "2025-12": 1.12, "2026-01": 1.05, "2026-03": 1.10}
# The Raya FD promo also pulls in organic sign-ups
ORGANIC_PROMO_LIFT = {"2025-03": 1.15, "2025-04": 1.15, "2025-05": 1.15}

# Marketing cost: paid media per applicant who starts sign-up,
# bonus schemes per account opened
COST_PER_START = {"google_search": 23.0, "meta_ads": 15.0, "tiktok": 8.5}
COST_PER_OPENED = {"affiliate": 18.0, "referral": 35.0}
AFFILIATE_PLATFORM_FEE = 1500.0

# ---------------------------------------------------------------------------
# Onboarding funnel (conditional pass rates between steps)
# ---------------------------------------------------------------------------
P_PHONE = {"default": 0.90, "tiktok": 0.86, "affiliate": 0.87}
P_ID_SCAN = 0.86
P_LIVENESS = {"control": 0.70, "guided": 0.77}   # story 2
P_EKYC_APPROVED = 0.95
P_ACCOUNT_OPENED = 0.97
P_MANUAL_REVIEW = 0.12

AB_TEST_START = date(2026, 2, 1)
AB_TEST_END = date(2026, 4, 30)
GUIDED_ROLLOUT = date(2026, 5, 1)

# Guardrail: accounts flagged by fraud monitoring within 30 days of opening
P_FRAUD_FLAG = {"control": 0.008, "guided": 0.008}

# ---------------------------------------------------------------------------
# Customer behaviour types (hidden: the k-means analysis has to find them)
# SAL salaried everyday banker, SAV saver, SPD card spender,
# OCC occasional user, HNT sign-up bonus hunter
# ---------------------------------------------------------------------------
TYPES = ["SAL", "SAV", "SPD", "OCC", "HNT"]
TYPE_MIX = {
    "organic":       [0.35, 0.20, 0.20, 0.20, 0.05],
    "google_search": [0.35, 0.25, 0.15, 0.20, 0.05],
    "meta_ads":      [0.28, 0.12, 0.22, 0.23, 0.15],
    "tiktok":        [0.04, 0.01, 0.07, 0.08, 0.80],   # story 1: mostly bonus hunters
    "referral":      [0.38, 0.18, 0.22, 0.17, 0.05],
    "affiliate":     [0.15, 0.08, 0.15, 0.17, 0.45],
}

# Monthly churn hazard after the opening month
CHURN_HAZARD = {"SAL": 0.015, "SAV": 0.010, "SPD": 0.025, "OCC": 0.050, "HNT": 0.080}
# Low-intent channels bring customers of every type who leave sooner
CHANNEL_CHURN_FACTOR = {"tiktok": 2.0, "affiliate": 1.5, "meta_ads": 1.2}
# Hunters mostly leave straight after collecting the bonus
HNT_EARLY_CHURN = {1: 0.70, 2: 0.15}
# Story 5: activating the debit card within 30 days halves the churn hazard
CARD_30D_HAZARD_FACTOR = 0.5
CARD_30D_HNT_EARLY_FACTOR = 0.6

# Chance of transacting in a month while still a customer
P_ACTIVE_MONTH = {"SAL": 0.97, "SAV": 0.80, "SPD": 0.97, "OCC": 0.50, "HNT": 0.60}

# Debit card
P_CARD_ISSUED = {"SAL": 0.85, "SAV": 0.60, "SPD": 0.97, "OCC": 0.60, "HNT": 0.50}
P_CARD_ACTIVE_30D = {"SAL": 0.75, "SAV": 0.45, "SPD": 0.92, "OCC": 0.40, "HNT": 0.18}
P_CARD_ACTIVE_LATER = 0.30

# Money in
P_SALARY_TO_KELIP = {"SAL": 0.70, "SAV": 0.35, "SPD": 0.45, "OCC": 0.10, "HNT": 0.0}
INCOME_MEDIAN = {"SAL": 4200, "SAV": 6500, "SPD": 3200, "OCC": 3000, "HNT": 2200}
INITIAL_DEPOSIT_MEDIAN = {"SAL": 800, "SAV": 12000, "SPD": 300, "OCC": 150, "HNT": 20}
DUITNOW_IN_RATE = {"SAL": 1.5, "SAV": 1.0, "SPD": 3.0, "OCC": 0.8, "HNT": 0.3}
DUITNOW_IN_MEDIAN = {"SAL": 300, "SAV": 1500, "SPD": 250, "OCC": 200, "HNT": 50}

# Money out: share of available funds spent in a month (beta distribution)
SPEND_FRACTION_BETA = {"SAL": (14, 3), "SAV": (2, 10), "SPD": (30, 1.5),
                       "OCC": (3, 3), "HNT": (9, 1)}
CARD_SHARE = {"SAL": 0.30, "SAV": 0.25, "SPD": 0.85, "OCC": 0.30, "HNT": 0.20}
BILL_SHARE = {"SAL": 0.20, "SAV": 0.25, "SPD": 0.10, "OCC": 0.20, "HNT": 0.0}
CARD_TXN_RATE = {"SAL": 5, "SAV": 2, "SPD": 18, "OCC": 2, "HNT": 1}
DUITNOW_OUT_RATE = {"SAL": 4, "SAV": 2, "SPD": 3, "OCC": 2, "HNT": 1}
BILL_RATE = {"SAL": 3, "SAV": 2, "SPD": 1, "OCC": 1, "HNT": 0}

# Churners: share who sweep their balance out, and who later close the account
P_CHURN_WITHDRAW = 0.60
P_CLOSE_AFTER_WITHDRAW = 0.35

# ---------------------------------------------------------------------------
# Card authorisations
# ---------------------------------------------------------------------------
# (mcc, category label, median RM, weight for SAL, SAV, SPD, OCC, HNT)
MERCHANTS = [
    (5411, "Groceries", 45, [0.22, 0.25, 0.14, 0.20, 0.15]),
    (5812, "Restaurants", 35, [0.12, 0.10, 0.13, 0.12, 0.10]),
    (5814, "Fast food", 18, [0.12, 0.08, 0.14, 0.14, 0.20]),
    (5399, "Online marketplaces", 60, [0.14, 0.10, 0.20, 0.14, 0.25]),
    (4121, "E-hailing and taxis", 22, [0.10, 0.06, 0.10, 0.10, 0.10]),
    (5541, "Fuel", 60, [0.10, 0.12, 0.07, 0.10, 0.05]),
    (4814, "Telco and bills", 50, [0.06, 0.08, 0.04, 0.06, 0.05]),
    (4899, "Streaming and subscriptions", 30, [0.04, 0.05, 0.06, 0.04, 0.05]),
    (4511, "Airlines and travel", 350, [0.02, 0.06, 0.03, 0.02, 0.01]),
    (5912, "Pharmacies", 40, [0.04, 0.06, 0.03, 0.04, 0.02]),
    (5651, "Clothing", 90, [0.03, 0.02, 0.04, 0.03, 0.01]),
    (5732, "Electronics", 250, [0.01, 0.02, 0.02, 0.01, 0.01]),
]
P_DECLINED_ATTEMPT = 0.05          # extra declined attempts, on top of approved spend
DECLINE_CODES = [("51", 0.60), ("55", 0.25), ("59", 0.15)]  # funds, PIN, suspected fraud
P_REVERSED = 0.01
# Days from authorisation to settlement; 4+ days counts as a late settlement
SETTLEMENT_LAG = [(0, 0.20), (1, 0.60), (2, 0.15), (3, 0.03), (5, 0.012), (8, 0.006), (12, 0.002)]
P_PROCESSOR_RESEND = 0.02

# ---------------------------------------------------------------------------
# Deposits (rates in % a year)
# ---------------------------------------------------------------------------
RATE_CUT_DATE = date(2025, 8, 1)   # Kelip passes on the 9 Jul 2025 OPR cut
CASA_RATE = {"before": 2.00, "after": 1.85}
FD_RATE = {6: {"before": 2.35, "after": 2.15}, 12: {"before": 2.50, "after": 2.30}}

# Standard FDs: monthly chance of placing one when savings exceed RM5,000
P_STANDARD_FD = {"SAL": 0.015, "SAV": 0.06, "SPD": 0.005, "OCC": 0.005, "HNT": 0.0}
STANDARD_FD_OUTCOME = {"rollover": 0.60, "to_casa": 0.30, "leave": 0.10}

# Story 3: the Raya FD promotion
PROMO_CODE = "RAYA25"
PROMO_START = date(2025, 3, 1)
PROMO_END = date(2025, 5, 31)
PROMO_RATE = 3.88
PROMO_TENOR = 6
P_PROMO_FD = {"SAL": 0.18, "SAV": 0.45, "SPD": 0.04, "OCC": 0.08, "HNT": 0.0}
PROMO_FROM_CASA_SHARE = (0.60, 0.90)   # share of the savings balance moved into the FD
P_PROMO_NEW_MONEY = 0.50               # also brings money in from another bank
PROMO_OUTCOME = {"rollover": 0.35, "to_casa": 0.30, "leave": 0.35}

# ---------------------------------------------------------------------------
# Personal financing (story 4)
# ---------------------------------------------------------------------------
PF_LAUNCH = date(2025, 1, 1)
# (policy code in the loan system, first month, last month, loans a month)
CREDIT_POLICIES = [
    ("CP-2025-01", "2025-01", "2025-06", (120, 200)),   # v1: standard
    ("CP-2025-07", "2025-07", "2025-12", (350, 450)),   # v2: loosened for growth
    ("CP-2026-01", "2026-01", "2026-08", (220, 280)),   # v3: tightened again
]
GRADE_MIX = {"CP-2025-01": [0.45, 0.40, 0.15, 0.00],
             "CP-2025-07": [0.25, 0.35, 0.28, 0.12],
             "CP-2026-01": [0.40, 0.40, 0.18, 0.02]}
DSR_RANGE = {"CP-2025-01": (15, 40), "CP-2025-07": (20, 60), "CP-2026-01": (15, 45)}
POLICY_RISK_FACTOR = {"CP-2025-01": 1.0, "CP-2025-07": 2.4, "CP-2026-01": 1.1}

GRADES = ["A", "B", "C", "D"]
GRADE_RATE = {"A": 7.5, "B": 10.5, "C": 14.5, "D": 18.5}
GRADE_PRINCIPAL_MEDIAN = {"A": 15000, "B": 10000, "C": 7000, "D": 5000}
GRADE_TENORS = {"A": ([36, 48, 60], [0.3, 0.4, 0.3]), "B": ([36, 48, 60], [0.4, 0.4, 0.2]),
                "C": ([24, 36], [0.5, 0.5]), "D": ([24, 36], [0.6, 0.4])}
BORROWER_TYPE_WEIGHT = {"SAL": 1.0, "SAV": 0.15, "SPD": 0.35, "OCC": 0.15, "HNT": 0.0}

# Monthly chance a current loan misses an instalment, before policy and age factors
P_MISS = {"A": 0.006, "B": 0.012, "C": 0.025, "D": 0.040}
MOB_FACTOR = {1: 0.8, 2: 0.8, 3: 1.3, 4: 1.3, 5: 1.3, 6: 1.3, 7: 1.3, 8: 1.3}
# From arrears (k instalments missed): cure all, pay one (stay), otherwise roll forward
P_CURE = {1: 0.35, 2: 0.22, 3: 0.12, 4: 0.05}
P_STAY = {1: 0.25, 2: 0.25, 3: 0.20, 4: 0.10}
P_PREPAY = 0.010
WRITE_OFF_AT_MISSED = 6
