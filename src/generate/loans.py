"""Personal financing: originations and the monthly loan tape (source 5).

Story 4: policy CP-2025-07 loosened approval for growth, so its vintages go
30+ days past due far more often than the policies either side of it.
"""

import numpy as np
import pandas as pd

from . import params as P
from .timeutil import (HOUR, MONTH_END_DATE, MONTH_LABELS, N_MONTHS, add_months,
                       random_times_in_month)


def _instalment(principal, annual_rate_pct, n):
    r = annual_rate_pct / 100 / 12
    return principal * r / (1 - (1 + r) ** (-n))


def _balance_after(principal, annual_rate_pct, instalment, k):
    """Scheduled principal outstanding after k instalments have been paid."""
    r = annual_rate_pct / 100 / 12
    g = (1 + r) ** k
    return np.maximum(principal * g - instalment * (g - 1) / r, 0.0)


def simulate_loans(rng, cust):
    """Pick borrowers, simulate repayment behaviour, and return loans, tape and cash events.

    cust needs: customer_idx, open_m, churn_k, type, income.
    """
    open_m = cust["open_m"].to_numpy()
    churn_k = cust["churn_k"].to_numpy()
    ctype = cust["type"].to_numpy()
    weight = np.array([P.BORROWER_TYPE_WEIGHT[t] for t in ctype])
    has_loan = np.zeros(len(cust), dtype=bool)

    loans = []
    for code, first, last, (lo, hi) in P.CREDIT_POLICIES:
        m0, m1 = MONTH_LABELS.index(first), MONTH_LABELS.index(last)
        for m in range(m0, m1 + 1):
            k = m - open_m
            eligible = (k >= 3) & (k < churn_k) & ~has_loan & (weight > 0)
            idx = np.flatnonzero(eligible)
            want = int(rng.integers(lo, hi + 1))
            take = min(want, len(idx))
            if take == 0:
                continue
            p = weight[idx] / weight[idx].sum()
            chosen = rng.choice(idx, size=take, replace=False, p=p)
            has_loan[chosen] = True
            grade = rng.choice(P.GRADES, size=take, p=P.GRADE_MIX[code])
            disb_ts = random_times_in_month(rng, m, take, hours=(10, 17))
            loans.append(pd.DataFrame({"customer_idx": chosen, "policy": code, "grade": grade,
                                       "disb_ts": disb_ts, "disb_m": m}))
    loans = pd.concat(loans, ignore_index=True).sort_values(["disb_ts", "customer_idx"]).reset_index(drop=True)
    n = len(loans)
    loans["loan_id"] = [f"PF{i:08d}" for i in range(1, n + 1)]
    grade = loans["grade"].to_numpy()
    policy = loans["policy"].to_numpy()

    med = np.array([P.GRADE_PRINCIPAL_MEDIAN[g] for g in grade])
    principal = np.clip(rng.lognormal(np.log(med), 0.5), 2000, 50000)
    principal = np.round(principal / 500) * 500
    tenor = np.empty(n, dtype=int)
    for g in P.GRADES:
        sel = grade == g
        opts, w = P.GRADE_TENORS[g]
        tenor[sel] = rng.choice(opts, size=sel.sum(), p=w)
    rate = np.array([P.GRADE_RATE[g] for g in grade], dtype=float)
    rate = np.where((policy == "CP-2026-01") & np.isin(grade, ["C", "D"]), rate + 0.5, rate)
    inst = np.round(_instalment(principal, rate, tenor), 2)
    dsr = np.array([rng.uniform(*P.DSR_RANGE[p]) for p in policy]).round(1)

    disb_ts = loans["disb_ts"].to_numpy(dtype="datetime64[s]")
    disb_d = disb_ts.astype("datetime64[D]")
    loans["application_date"] = disb_d - rng.integers(1, 6, n)
    loans["principal"] = principal
    loans["tenor_months"] = tenor
    loans["rate_pct"] = rate
    loans["instalment"] = inst
    loans["dsr_pct"] = dsr

    # --- Monthly repayment behaviour -------------------------------------------------
    paid = np.zeros(n, dtype=int)            # instalments paid so far
    status = np.full(n, "ACTIVE", dtype=object)
    closed_m = np.full(n, 10**6)
    disb_m = loans["disb_m"].to_numpy()
    risk = np.array([P.P_MISS[g] for g in grade]) * np.array([P.POLICY_RISK_FACTOR[p] for p in policy])

    tape = []
    cash = []   # (loan idx, MYT timestamp, amount RM, kind)
    cash.append(pd.DataFrame({"loan": np.arange(n), "ts": disb_ts, "amount": principal, "kind": "disbursement"}))

    # due date of instalment j (1-based) is disbursement date + j months
    max_tenor = tenor.max()
    due = np.stack([add_months(disb_d, j) for j in range(1, max_tenor + 1)], axis=1)  # n x max_tenor

    for m in range(disb_m.min(), N_MONTHS):
        live = (disb_m <= m) & (status == "ACTIVE")
        month_end = MONTH_END_DATE[m]
        idx = np.flatnonzero(live)
        if len(idx) == 0:
            continue
        # Instalments count as due once their due date has passed (strictly before the
        # month-end snapshot), so an instalment falling due on the last day is not yet in arrears
        due_by = (due[idx] < month_end).sum(axis=1)
        due_by = np.minimum(due_by, tenor[idx])
        prev_due = (due[idx] < MONTH_END_DATE[m - 1]).sum(axis=1) if m > 0 else np.zeros(len(idx), int)
        prev_due = np.minimum(prev_due, tenor[idx])
        new_due = due_by - prev_due
        arrears_before = prev_due - paid[idx]
        mob = m - disb_m[idx]
        u = rng.random(len(idx))

        new_paid = paid[idx].copy()
        pay_ts_kind = np.zeros(len(idx), dtype=int)   # 0 none, 1 on due date, 2 catch-up in month
        current = arrears_before == 0
        # Current loans: pay this month's instalment unless they miss it
        mob_f = np.array([P.MOB_FACTOR.get(x, 1.0) for x in mob])
        miss = current & (new_due > 0) & (u < risk[idx] * mob_f)
        pay_now = current & (new_due > 0) & ~miss
        new_paid[pay_now] += new_due[pay_now]
        pay_ts_kind[pay_now] = 1
        # Loans in arrears: cure fully, pay one, or roll forward
        arr = ~current
        k = np.minimum(arrears_before, 4)
        p_cure = np.array([P.P_CURE.get(x, 0) for x in k])
        p_stay = np.array([P.P_STAY.get(x, 0) for x in k])
        cure = arr & (u < p_cure)
        stay = arr & ~cure & (u < p_cure + p_stay)
        new_paid[cure] = due_by[cure]
        new_paid[stay] = np.minimum(new_paid[stay] + np.maximum(new_due[stay], 1), due_by[stay])
        pay_ts_kind[cure | stay] = 2

        n_paid_now = new_paid - paid[idx]
        # Cash events for instalments paid this month
        has_pay = n_paid_now > 0
        if has_pay.any():
            li = idx[has_pay]
            on_due = pay_ts_kind[has_pay] == 1
            # on-time payments land on the due date; one due on last month's final day is
            # collected by the auto-debit run on the first morning of this month
            last_due = due[li, np.clip(due_by[has_pay] - 1, 0, None)]
            first_day = MONTH_END_DATE[m - 1] + 1 if m > 0 else last_due
            ts_due = (np.maximum(last_due, first_day).astype("datetime64[s]")
                      + rng.integers(7, 10, has_pay.sum()) * HOUR)
            ts_catch = random_times_in_month(rng, m, has_pay.sum(), hours=(9, 22))
            ts = np.where(on_due, ts_due, ts_catch)
            cash.append(pd.DataFrame({"loan": li, "ts": ts, "amount": n_paid_now[has_pay] * inst[li],
                                      "kind": "repayment"}))
        paid[idx] = new_paid

        # Early settlement by some current, up-to-date loans
        up_to_date = paid[idx] >= due_by
        prepay = up_to_date & (rng.random(len(idx)) < P.P_PREPAY) & (paid[idx] < tenor[idx])
        if prepay.any():
            li = idx[prepay]
            bal = _balance_after(principal[li], rate[li], inst[li], paid[li])
            ts = random_times_in_month(rng, m, prepay.sum(), hours=(9, 22))
            cash.append(pd.DataFrame({"loan": li, "ts": ts, "amount": np.round(bal, 2), "kind": "settlement"}))
            status[li] = "SETTLED"
            closed_m[li] = m
        finished = (paid[idx] >= tenor[idx]) & (status[idx] == "ACTIVE")
        status[idx[finished]] = "SETTLED"
        closed_m[idx[finished]] = m

        arrears_now = due_by - paid[idx]
        written = (arrears_now >= P.WRITE_OFF_AT_MISSED) & (status[idx] == "ACTIVE")
        status[idx[written]] = "WRITTEN_OFF"
        closed_m[idx[written]] = m

        # Days past due at month end: days since the oldest unpaid due date
        oldest_unpaid = due[idx, np.clip(paid[idx], 0, max_tenor - 1)]
        dpd = np.where(arrears_now > 0, (month_end - oldest_unpaid).astype(int), 0)
        dpd = np.maximum(dpd, 0)
        outstanding = _balance_after(principal[idx], rate[idx], inst[idx], paid[idx])
        st = status[idx]
        outstanding = np.where(st == "SETTLED", 0.0, outstanding)
        tape.append(pd.DataFrame({
            "loan": idx, "snapshot_date": month_end, "outstanding_principal": np.round(outstanding, 2),
            "instalments_due": due_by, "instalments_paid": paid[idx], "days_past_due": dpd,
            "loan_status": st,
        }))

    tape = pd.concat(tape, ignore_index=True)
    cash = pd.concat(cash, ignore_index=True)
    cash["amount"] = np.round(cash["amount"].astype(float), 2)
    return loans, tape, cash
