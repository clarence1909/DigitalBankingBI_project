"""Customers, accounts, ledger postings, month-end balances and card activity.

Sources produced here:
  2. core banking: customers, accounts and month-end account balances
  3. the posting engine: ledger postings
  4. the card processor: card authorisations

Money is held in integer sen throughout, so balances tie to the ledger exactly.
Balances are tracked month by month from the postings themselves, which is
what makes the ledger-to-balance reconciliation tie to the sen.
"""

import numpy as np
import pandas as pd

from src.config import DATA_END

from . import params as P
from .timeutil import (DAY, DAYS_IN_MONTH, END_TS, HOUR, MINUTE, MONTH_END_DATE, MONTH_LABELS,
                       MONTH_START, N_MONTHS, SECOND, add_months, month_index, random_times_in_month, sen)

TYPE_INDEX = {t: i for i, t in enumerate(P.TYPES)}
MCC = np.array([m[0] for m in P.MERCHANTS])
MCC_MEDIAN = np.array([m[2] for m in P.MERCHANTS], dtype=float)
MCC_WEIGHTS = np.array([m[3] for m in P.MERCHANTS], dtype=float)   # merchants x types
MCC_WEIGHTS = MCC_WEIGHTS / MCC_WEIGHTS.sum(axis=0, keepdims=True)
DATA_END_D = np.datetime64(DATA_END)


def _by_type(values, types):
    return np.array([values[t] for t in P.TYPES])[types]


def build_customers(rng, app):
    """One row per applicant who opened an account, with hidden behaviour traits."""
    opened = app[app["account_opened"]].sort_values(["t_open", "applicant_id"]).reset_index(drop=True)
    n = len(opened)
    cust = pd.DataFrame({
        "customer_id": [f"C{i:07d}" for i in range(1, n + 1)],
        "casa_id": [f"SA{i:08d}" for i in range(1, n + 1)],
        "applicant_id": opened["applicant_id"],
        "channel": opened["channel"],
        "ekyc_flow": opened["ekyc_flow"],
        "open_ts": opened["t_open"].to_numpy(dtype="datetime64[s]"),
    })
    open_ts = cust["open_ts"].to_numpy(dtype="datetime64[s]")
    cust["open_m"] = month_index(open_ts)

    ch = cust["channel"].to_numpy()
    t = np.empty(n, dtype=int)
    for c in P.CHANNELS:
        sel = ch == c
        t[sel] = rng.choice(len(P.TYPES), size=sel.sum(), p=P.TYPE_MIX[c])
    cust["type_idx"] = t
    cust["type"] = np.array(P.TYPES)[t]

    # Demographics
    age = np.clip(18 + rng.gamma(4.0, 3.2, n), 18, 70).astype(int)
    age[t == TYPE_INDEX["SAV"]] = np.clip(age[t == TYPE_INDEX["SAV"]] + 8, 18, 75)
    cust["birth_year"] = open_ts.astype("datetime64[Y]").astype(int) + 1970 - age
    from .mess import STATE_WEIGHTS
    states = list(STATE_WEIGHTS)
    w = np.array(list(STATE_WEIGHTS.values()))
    cust["state"] = rng.choice(states, size=n, p=w / w.sum())
    emp_by_type = {
        "SAL": (["salaried", "self_employed"], [0.92, 0.08]),
        "SAV": (["salaried", "self_employed", "retired"], [0.55, 0.25, 0.20]),
        "SPD": (["salaried", "self_employed", "student"], [0.60, 0.15, 0.25]),
        "OCC": (["salaried", "self_employed", "student", "not_working"], [0.45, 0.20, 0.20, 0.15]),
        "HNT": (["student", "salaried", "not_working"], [0.50, 0.30, 0.20]),
    }
    emp = np.empty(n, dtype=object)
    for ty, (opts, pw) in emp_by_type.items():
        sel = cust["type"].to_numpy() == ty
        emp[sel] = rng.choice(opts, size=sel.sum(), p=pw)
    cust["employment"] = emp
    income = rng.lognormal(np.log(_by_type(P.INCOME_MEDIAN, t)), 0.40)
    cust["income"] = np.round(income, -1)
    cust["salary_to_kelip"] = rng.random(n) < _by_type(P.P_SALARY_TO_KELIP, t)
    cust["salary_day"] = rng.integers(25, 29, n)
    cust["risk_rating"] = rng.choice(["low", "medium", "high"], size=n, p=[0.82, 0.15, 0.03])

    # Debit card: issued at onboarding, activated early, late or never
    issued = rng.random(n) < _by_type(P.P_CARD_ISSUED, t)
    early = issued & (rng.random(n) < _by_type(P.P_CARD_ACTIVE_30D, t))
    late = issued & ~early & (rng.random(n) < P.P_CARD_ACTIVE_LATER)
    act = np.full(n, np.datetime64("NaT"), dtype="datetime64[s]")
    act[early] = open_ts[early] + (np.minimum(rng.exponential(5 * 86400, early.sum()), 29 * 86400)
                                   + 600).astype(int) * SECOND
    act[late] = open_ts[late] + rng.integers(31 * 86400, 120 * 86400, late.sum()) * SECOND
    act[act > END_TS] = np.datetime64("NaT")
    cust["card_issued"] = issued
    cust["card_act_ts"] = act
    cust["card_active_30d"] = early
    cust["card_id"] = np.where(issued, [f"DC{i:08d}" for i in range(1, n + 1)], None)

    # Churn: the month (since opening) from which the customer stops banking with Kelip
    ctype = cust["type"].to_numpy()
    haz = _by_type(P.CHURN_HAZARD, t) * np.array([P.CHANNEL_CHURN_FACTOR.get(c, 1.0) for c in ch])
    haz = np.where(early, haz * P.CARD_30D_HAZARD_FACTOR, haz)
    churn_k = rng.geometric(np.clip(haz, 1e-4, 1))
    hnt = ctype == "HNT"
    u = rng.random(n)
    f = np.where(early, P.CARD_30D_HNT_EARLY_FACTOR, 1.0)
    p1, p2 = P.HNT_EARLY_CHURN[1] * f, P.HNT_EARLY_CHURN[2] * f
    hnt_k = np.where(u < p1, 1, np.where(u < p1 + p2, 2, 2 + rng.geometric(np.clip(haz, 1e-4, 1))))
    churn_k[hnt] = hnt_k[hnt]
    cust["churn_k"] = churn_k

    # Guardrail metric for the eKYC test: flagged by fraud monitoring within 30 days
    p_flag = np.where(cust["ekyc_flow"].to_numpy() == "guided", P.P_FRAUD_FLAG["guided"], P.P_FRAUD_FLAG["control"])
    flagged = rng.random(n) < p_flag
    flag_ts = open_ts + rng.integers(1, 30, n) * DAY
    cust["fraud_flag_date"] = np.where(flagged & (flag_ts <= END_TS), flag_ts.astype("datetime64[D]"),
                                       np.datetime64("NaT"))
    return cust


TXN_TYPES = ["salary", "duitnow_in", "duitnow_out", "bill_payment", "card_purchase", "interest",
             "fd_placement", "fd_maturity", "fd_rollover", "pf_disbursement", "pf_repayment"]
TXN_ID = {name: i for i, name in enumerate(TXN_TYPES)}


class Ledger:
    """Collects postings month by month (MYT timestamps, amounts in sen).

    Parts are kept as plain arrays and joined once at the end, which is far
    quicker than building a small table for every batch. Account kind and
    transaction type are small integers until the writer turns them into text.
    """

    COLS = ["is_fd", "idx", "ts", "amount", "sign", "txn", "ref"]

    def __init__(self):
        self.parts = []

    def add(self, kind, idx, ts, amount, sign, txn, ref=None):
        idx = np.asarray(idx)
        if len(idx) == 0:
            return
        amount = np.asarray(amount, dtype=np.int64)
        ts = np.asarray(ts, dtype="datetime64[s]")
        if ref is None:
            ref = np.full(len(idx), None, dtype=object)
        else:
            ref = np.asarray(ref, dtype=object)
        keep = amount > 0
        if not keep.all():
            idx, ts, amount, ref = idx[keep], ts[keep], amount[keep], ref[keep]
        if len(idx) == 0:
            return
        k = len(idx)
        self.parts.append((np.full(k, kind == "fd"), idx, ts, amount,
                           np.full(k, sign, dtype=np.int8), np.full(k, TXN_ID[txn], dtype=np.int8), ref))

    def frame(self):
        cols = list(zip(*self.parts))
        return pd.DataFrame({name: np.concatenate(arrs) for name, arrs in zip(self.COLS, cols)})


def _split(rng, budgets, counts, raw_sizes):
    """Split each owner's budget (sen) across their transactions in proportion to raw sizes."""
    owner = np.repeat(np.arange(len(budgets)), counts)
    if len(owner) == 0:
        return owner, np.array([], dtype=np.int64)
    tot = np.bincount(owner, weights=raw_sizes, minlength=len(budgets))
    amt = np.floor(raw_sizes / tot[owner] * budgets[owner]).astype(np.int64)
    rem = budgets - np.bincount(owner, weights=amt, minlength=len(budgets)).astype(np.int64)
    starts = np.cumsum(counts) - counts
    has = counts > 0
    amt[starts[has]] += rem[has]
    return owner, amt


def simulate_banking(rng, cust, loans, loan_cash):
    n = len(cust)
    t = cust["type_idx"].to_numpy()
    ctype = cust["type"].to_numpy()
    open_ts = cust["open_ts"].to_numpy(dtype="datetime64[s]")
    open_m = cust["open_m"].to_numpy()
    churn_k = cust["churn_k"].to_numpy()
    act_ts = cust["card_act_ts"].to_numpy(dtype="datetime64[s]")
    salary_to = cust["salary_to_kelip"].to_numpy()
    income = cust["income"].to_numpy()
    salary_day = cust["salary_day"].to_numpy()

    has_loan = np.zeros(n, dtype=bool)
    has_loan[loans["customer_idx"].to_numpy()] = True
    loan_cust = loans["customer_idx"].to_numpy()
    loan_ids = loans["loan_id"].to_numpy()
    lc = loan_cash.copy()
    lc["cust"] = loan_cust[lc["loan"].to_numpy()]
    lc["ref"] = loan_ids[lc["loan"].to_numpy()]
    lc["m"] = month_index(lc["ts"].to_numpy(dtype="datetime64[s]"))
    lc["sen"] = sen(lc["amount"].to_numpy())

    bal = np.zeros(n, dtype=np.int64)          # exact CASA balance at the end of the month so far
    pending = np.zeros(n, dtype=np.int64)      # card settlements that post next month
    pending_rows = None
    closed = np.zeros(n, dtype=bool)
    close_ts = np.full(n, np.datetime64("NaT"), dtype="datetime64[s]")
    close_m = np.full(n, 10**6)
    withdrew = np.zeros(n, dtype=bool)
    promo_done = np.zeros(n, dtype=bool)
    ever_fd = np.zeros(n, dtype=bool)

    fd = {k: [] for k in ["cust", "open_ts", "principal", "rate", "tenor", "maturity", "product",
                          "promo", "rollover_of", "outcome"]}
    fd_status = []
    fd_close = []
    leave_queue = []   # (cust idx, ts, amount sen) outflows after promo money leaves
    ledger = Ledger()
    card_parts = []

    p_active = _by_type(P.P_ACTIVE_MONTH, t)
    promo_months = {MONTH_LABELS.index(f"{P.PROMO_START:%Y-%m}") + i for i in range(3)}
    h_promo = 1 - (1 - _by_type(P.P_PROMO_FD, t)) ** (1 / 3)
    p_std_fd = _by_type(P.P_STANDARD_FD, t)
    spend_a = np.array([P.SPEND_FRACTION_BETA[x][0] for x in P.TYPES])[t]
    spend_b = np.array([P.SPEND_FRACTION_BETA[x][1] for x in P.TYPES])[t]
    card_share = _by_type(P.CARD_SHARE, t)
    bill_share = _by_type(P.BILL_SHARE, t)

    def new_fd(ci, ts, principal, tenor, promo, rollover_of, outcome_probs):
        k = len(ci)
        if k == 0:
            return np.array([], dtype=int)
        d = ts.astype("datetime64[D]")
        after = d >= np.datetime64(P.RATE_CUT_DATE)
        if promo:
            rate = np.full(k, P.PROMO_RATE)
            product = np.full(k, "FD-RAYA25", dtype=object)
        else:
            rate = np.array([P.FD_RATE[te]["after" if a else "before"] for te, a in zip(tenor, after)])
            product = np.where(np.asarray(tenor) == 6, "FD-06M", "FD-12M").astype(object)
        outcome = rng.choice(list(outcome_probs), size=k, p=list(outcome_probs.values()))
        start = len(fd["cust"])
        fd["cust"].extend(ci)
        fd["open_ts"].extend(ts)
        fd["principal"].extend(principal)
        fd["rate"].extend(rate)
        fd["tenor"].extend(tenor)
        fd["maturity"].extend(add_months(d, tenor))
        fd["product"].extend(product)
        fd["promo"].extend([promo] * k)
        fd["rollover_of"].extend(rollover_of)
        fd["outcome"].extend(outcome)
        fd_status.extend(["ACTIVE"] * k)
        fd_close.extend([np.datetime64("NaT", "D")] * k)
        ever_fd[ci] = True
        return np.arange(start, start + k)

    for m in range(N_MONTHS):
        m_start, m_end_d = MONTH_START[m], MONTH_END_DATE[m]
        m_end_ts = m_start + DAYS_IN_MONTH[m] * DAY - SECOND
        bal_start = bal.copy()
        alive = (open_m <= m) & ~closed
        k = m - open_m
        churned_now = alive & (k == churn_k)
        pool = alive & (k < churn_k)
        active = pool & ((k == 0) | (rng.random(n) < p_active))
        credit = np.zeros(n, dtype=np.int64)
        debit = np.zeros(n, dtype=np.int64)

        def post_casa(idx, ts, amount, sign, txn, ref=None):
            amount = np.asarray(amount, dtype=np.int64)
            ledger.add("casa", idx, ts, amount, sign, txn, ref)
            np.add.at(credit if sign > 0 else debit, np.asarray(idx), amount)

        # --- Money in -----------------------------------------------------------------
        newc = np.flatnonzero(alive & (k == 0))
        amt = rng.lognormal(np.log(_by_type(P.INITIAL_DEPOSIT_MEDIAN, t[newc])), 0.9)
        hn = ctype[newc] == "HNT"
        amt[hn] = rng.uniform(10, 50, hn.sum())
        dep_ts = np.minimum(open_ts[newc] + rng.integers(60, 1800, len(newc)) * SECOND, m_end_ts)
        post_casa(newc, dep_ts, sen(amt), +1, "duitnow_in")

        sal = np.flatnonzero(active & salary_to)
        sal_ts = (m_start + (salary_day[sal] - 1) * DAY + rng.integers(8 * 3600, 10 * 3600, len(sal)) * SECOND)
        ok = sal_ts > open_ts[sal]
        sal, sal_ts = sal[ok], sal_ts[ok]
        post_casa(sal, sal_ts, sen(income[sal] * rng.uniform(0.97, 1.03, len(sal))), +1, "salary")

        act_idx = np.flatnonzero(active)
        n_in = rng.poisson(_by_type(P.DUITNOW_IN_RATE, t[act_idx]))
        own = np.repeat(act_idx, n_in)
        if len(own):
            amt = rng.lognormal(np.log(_by_type(P.DUITNOW_IN_MEDIAN, t[own])), 0.9)
            post_casa(own, random_times_in_month(rng, m, len(own), not_before=open_ts[own] + MINUTE),
                      sen(amt), +1, "duitnow_in")

        lcm = lc[lc["m"] == m]
        disb = lcm[lcm["kind"] == "disbursement"]
        post_casa(disb["cust"].to_numpy(), disb["ts"].to_numpy(dtype="datetime64[s]"), disb["sen"].to_numpy(),
                  +1, "pf_disbursement", disb["ref"].to_numpy(dtype=object))

        # --- Fixed deposits maturing this month -----------------------------------------
        if fd["cust"]:
            mat = np.array(fd["maturity"], dtype="datetime64[D]")
            status = np.array(fd_status, dtype=object)
            due = np.flatnonzero((status == "ACTIVE") & (mat >= m_start.astype("datetime64[D]")) & (mat <= m_end_d))
            if len(due):
                principal = np.array(fd["principal"], dtype=np.int64)[due]
                rate = np.array(fd["rate"])[due]
                opened_d = np.array(fd["open_ts"], dtype="datetime64[s]")[due].astype("datetime64[D]")
                days = (mat[due] - opened_d).astype(int)
                interest = np.round(principal * rate / 100 * days / 365).astype(np.int64)
                total = principal + interest
                ts_int = mat[due].astype("datetime64[s]") + 30 * MINUTE
                ts_out = ts_int + MINUTE
                fd_ids = np.array([f"FD{j + 1:08d}" for j in due], dtype=object)
                ledger.add("fd", due, ts_int, interest, +1, "interest")
                outcome = np.array(fd["outcome"], dtype=object)[due]
                ci = np.array(fd["cust"])[due]
                # a closed savings account cannot receive money: roll over instead
                outcome = np.where(closed[ci], "rollover", outcome)
                roll = outcome == "rollover"
                ledger.add("fd", due[roll], ts_out[roll], total[roll], -1, "fd_rollover")
                tenor = np.array(fd["tenor"])[due]
                new_idx = new_fd(ci[roll], ts_out[roll], total[roll], tenor[roll], False,
                                 list(due[roll]), P.STANDARD_FD_OUTCOME)
                if len(new_idx):
                    ledger.add("fd", new_idx, ts_out[roll], total[roll], +1, "fd_rollover", fd_ids[roll])
                back = ~roll
                ledger.add("fd", due[back], ts_out[back], total[back], -1, "fd_maturity")
                post_casa(ci[back], ts_out[back], total[back], +1, "fd_maturity", fd_ids[back])
                for j in due:
                    fd_status[j] = "MATURED"
                    fd_close[j] = mat[j]
                leave = back & (outcome == "leave")
                if leave.any():
                    lts = ts_out[leave] + (rng.integers(1, 15, leave.sum()) * DAY
                                           + rng.integers(10 * 3600, 22 * 3600, leave.sum()) * SECOND)
                    lam = (total[leave] * rng.uniform(0.8, 1.0, leave.sum())).astype(np.int64)
                    leave_queue.extend(zip(ci[leave], lts, lam))

        # --- Money out that must happen -------------------------------------------------
        rep = lcm[lcm["kind"] != "disbursement"]
        rep_c = rep["cust"].to_numpy()
        rep_amt = rep["sen"].to_numpy()
        rep_ts = rep["ts"].to_numpy(dtype="datetime64[s]")
        need = np.zeros(n, dtype=np.int64)
        np.add.at(need, rep_c, rep_amt)
        # customers top up from another bank when a repayment would overdraw them
        short = bal + credit - debit - pending - need
        top = np.flatnonzero(short < 0)
        if len(top):
            first_rep = pd.Series(rep_ts).groupby(rep_c).min()
            tts = first_rep.reindex(top).to_numpy(dtype="datetime64[s]") - rng.integers(1, 6, len(top)) * HOUR
            tts = np.where(np.isnat(tts), m_start + 30 * MINUTE, tts)
            tts = np.maximum(tts, m_start + MINUTE)
            post_casa(top, tts, -short[top] + sen(rng.uniform(20, 60, len(top))), +1, "duitnow_in")
        post_casa(rep_c, rep_ts, rep_amt, -1, "pf_repayment", rep["ref"].to_numpy(dtype=object))

        # Card settlements carried over from last month
        if pending_rows is not None and len(pending_rows):
            post_casa(pending_rows["cust"].to_numpy(), pending_rows["post_ts"].to_numpy(dtype="datetime64[s]"),
                      pending_rows["amount"].to_numpy(), -1, "card_purchase",
                      pending_rows["auth_key"].to_numpy(dtype=object))
        pending[:] = 0

        # Promo money leaving after maturity
        if leave_queue:
            q = pd.DataFrame(leave_queue, columns=["cust", "ts", "amt"])
            qm = month_index(q["ts"].to_numpy(dtype="datetime64[s]"))
            now = q[qm == m]
            leave_queue = [row for row, keep in zip(leave_queue, qm > m) if keep]
            if len(now):
                c = now["cust"].to_numpy()
                avail = np.maximum(bal[c] + credit[c] - debit[c], 0)
                amt = np.minimum(now["amt"].to_numpy(dtype=np.int64), avail)
                post_casa(c, now["ts"].to_numpy(dtype="datetime64[s]"), amt, -1, "duitnow_out")

        # Fixed deposit placements
        funds = bal + credit - debit
        if m in promo_months:
            elig = np.flatnonzero(active & ~promo_done & (funds >= sen(1000)))
            take = elig[rng.random(len(elig)) < h_promo[elig]]
            if len(take):
                from_casa = (funds[take] * rng.uniform(*P.PROMO_FROM_CASA_SHARE, len(take))) // 10000 * 10000
                new_money = np.where(rng.random(len(take)) < P.P_PROMO_NEW_MONEY,
                                     (from_casa * rng.uniform(0.2, 1.0, len(take))) // 10000 * 10000, 0)
                ts = random_times_in_month(rng, m, len(take), not_before=open_ts[take] + HOUR)
                post_casa(take, ts - rng.integers(10, 120, len(take)) * MINUTE, new_money, +1, "duitnow_in")
                principal = from_casa + new_money
                ok = principal >= sen(1000)
                take, ts, principal = take[ok], ts[ok], principal[ok]
                ids = new_fd(take, ts, principal, np.full(len(take), P.PROMO_TENOR), True,
                             [-1] * len(take), P.PROMO_OUTCOME)
                post_casa(take, ts, principal, -1, "fd_placement",
                          np.array([f"FD{j + 1:08d}" for j in ids], dtype=object))
                ledger.add("fd", ids, ts, principal, +1, "fd_placement", np.array(cust["casa_id"].to_numpy()[take]))
                promo_done[take] = True
        else:
            funds = bal + credit - debit
            elig = np.flatnonzero(active & (funds >= sen(5000)))
            take = elig[rng.random(len(elig)) < p_std_fd[elig]]
            if len(take):
                principal = (funds[take] * rng.uniform(0.3, 0.7, len(take))) // 10000 * 10000
                ok = principal >= sen(1000)
                take, principal = take[ok], principal[ok]
                tenor = np.where(rng.random(len(take)) < 0.6, 12, 6)
                ts = random_times_in_month(rng, m, len(take), not_before=open_ts[take] + HOUR)
                ids = new_fd(take, ts, principal, tenor, False, [-1] * len(take), P.STANDARD_FD_OUTCOME)
                post_casa(take, ts, principal, -1, "fd_placement",
                          np.array([f"FD{j + 1:08d}" for j in ids], dtype=object))
                ledger.add("fd", ids, ts, principal, +1, "fd_placement", np.array(cust["casa_id"].to_numpy()[take]))

        # Churners sweep their money out, and some close the account later
        funds = bal + credit - debit
        sweep = np.flatnonzero(churned_now & (rng.random(n) < P.P_CHURN_WITHDRAW))
        if len(sweep):
            amt = (np.maximum(funds[sweep], 0) * rng.uniform(0.9, 1.0, len(sweep))).astype(np.int64)
            ts = random_times_in_month(rng, m, len(sweep), not_before=np.maximum(open_ts[sweep], m_start + 10 * DAY))
            post_casa(sweep, ts, amt, -1, "duitnow_out")
            withdrew[sweep] = True
            closer = sweep[(rng.random(len(sweep)) < P.P_CLOSE_AFTER_WITHDRAW) & ~has_loan[sweep] & ~ever_fd[sweep]]
            close_m[closer] = m + rng.integers(1, 4, len(closer))

        # --- Everyday spending ------------------------------------------------------------
        funds = bal + credit - debit
        spender = active & ~churned_now & (funds > sen(20))
        s_idx = np.flatnonzero(spender)
        frac = rng.beta(spend_a[s_idx], spend_b[s_idx])
        budget = ((funds[s_idx] - sen(20)) * frac).astype(np.int64)
        card_ok = ~np.isnat(act_ts[s_idx]) & (act_ts[s_idx] <= m_end_ts)
        card_b = np.where(card_ok, (budget * card_share[s_idx]).astype(np.int64), 0)
        bill_b = (budget * bill_share[s_idx]).astype(np.int64)
        dn_b = budget - card_b - bill_b

        # Card purchases: the processor sees authorisations; the ledger sees settlements
        n_card = np.where(card_b >= sen(5), np.maximum(rng.poisson(_by_type(P.CARD_TXN_RATE, t[s_idx])), 1), 0)
        n_card = np.minimum(n_card, card_b // sen(2))
        own_rel = np.repeat(np.arange(len(s_idx)), n_card)
        owner = s_idx[own_rel]
        merchant = np.empty(len(owner), dtype=int)
        for ty in range(len(P.TYPES)):
            sel = t[owner] == ty
            merchant[sel] = rng.choice(len(MCC), size=sel.sum(), p=MCC_WEIGHTS[:, ty])
        raw = rng.lognormal(np.log(MCC_MEDIAN[merchant]), 0.6)
        _, amounts = _split(rng, card_b, n_card, raw)
        big_enough = amounts >= 100          # nothing under RM1 on a card
        owner, merchant, amounts = owner[big_enough], merchant[big_enough], amounts[big_enough]
        not_before = np.maximum(open_ts[owner], np.where(np.isnat(act_ts[owner]), open_ts[owner], act_ts[owner]))
        auth_ts = random_times_in_month(rng, m, len(owner), not_before=not_before + MINUTE)
        lag_days, lag_p = zip(*P.SETTLEMENT_LAG)
        lag = rng.choice(lag_days, size=len(owner), p=np.array(lag_p) / sum(lag_p))
        settle = auth_ts.astype("datetime64[D]") + lag
        reversed_ = rng.random(len(owner)) < P.P_REVERSED
        settled = ~reversed_ & (settle <= DATA_END_D)
        auth_key = np.array([f"{m:02d}-{i:07d}" for i in range(len(owner))], dtype=object)
        post_ts = settle.astype("datetime64[s]") + rng.integers(3600, 4 * 3600, len(owner)) * SECOND
        now_post = settled & (settle <= m_end_d)
        later = settled & (settle > m_end_d)
        post_casa(owner[now_post], post_ts[now_post], amounts[now_post], -1, "card_purchase", auth_key[now_post])
        pending_rows = pd.DataFrame({"cust": owner[later], "post_ts": post_ts[later],
                                     "amount": amounts[later], "auth_key": auth_key[later]})
        np.add.at(pending, owner[later], amounts[later])
        status = np.where(reversed_, "REVERSED", "APPROVED").astype(object)
        card_parts.append(pd.DataFrame({
            "cust": owner, "auth_ts": auth_ts, "amount_sen": amounts, "mcc": MCC[merchant],
            "status": status, "response_code": "00", "settle": np.where(settled, settle, np.datetime64("NaT")),
            "auth_key": auth_key,
        }))
        # Declined attempts (insufficient funds, wrong PIN, suspected fraud) never post
        n_dec = rng.binomial(n_card, P.P_DECLINED_ATTEMPT)
        downer = s_idx[np.repeat(np.arange(len(s_idx)), n_dec)]
        if len(downer):
            dm = np.empty(len(downer), dtype=int)
            for ty in range(len(P.TYPES)):
                sel = t[downer] == ty
                dm[sel] = rng.choice(len(MCC), size=sel.sum(), p=MCC_WEIGHTS[:, ty])
            codes, cp = zip(*P.DECLINE_CODES)
            nb = np.where(np.isnat(act_ts[downer]), open_ts[downer], act_ts[downer])
            card_parts.append(pd.DataFrame({
                "cust": downer,
                "auth_ts": random_times_in_month(rng, m, len(downer), not_before=nb + MINUTE),
                "amount_sen": sen(rng.lognormal(np.log(MCC_MEDIAN[dm]) + 0.4, 0.7)),
                "mcc": MCC[dm], "status": "DECLINED",
                "response_code": rng.choice(codes, size=len(downer), p=cp),
                "settle": np.datetime64("NaT"), "auth_key": None,
            }))

        # Bill payments and DuitNow transfers out
        n_bill = np.where(bill_b >= sen(5), np.maximum(rng.poisson(_by_type(P.BILL_RATE, t[s_idx])), 1), 0)
        n_bill = np.where(bill_share[s_idx] > 0, n_bill, 0)
        own_rel = np.repeat(np.arange(len(s_idx)), n_bill)
        _, bamt = _split(rng, bill_b, n_bill, rng.lognormal(0, 0.5, len(own_rel)))
        bown = s_idx[own_rel]
        keep = bamt >= 100
        bown, bamt = bown[keep], bamt[keep]
        post_casa(bown, random_times_in_month(rng, m, len(bown), not_before=open_ts[bown] + MINUTE), bamt, -1,
                  "bill_payment")
        n_dn = np.where(dn_b >= sen(5), np.maximum(rng.poisson(_by_type(P.DUITNOW_OUT_RATE, t[s_idx])), 1), 0)
        own_rel = np.repeat(np.arange(len(s_idx)), n_dn)
        _, damt = _split(rng, dn_b, n_dn, rng.lognormal(0, 0.8, len(own_rel)))
        down = s_idx[own_rel]
        keep = damt >= 100
        down, damt = down[keep], damt[keep]
        post_casa(down, random_times_in_month(rng, m, len(down), not_before=open_ts[down] + MINUTE), damt, -1,
                  "duitnow_out")

        # Accounts closing this month: sweep what is left, no interest after closing
        closing = np.flatnonzero(alive & (close_m == m))
        if len(closing):
            cts = random_times_in_month(rng, m, len(closing), hours=(9, 18))
            amt = bal[closing] + credit[closing] - debit[closing]
            post_casa(closing, cts, np.maximum(amt, 0), -1, "duitnow_out")
            closed[closing] = True
            close_ts[closing] = cts

        # Monthly interest on savings, credited on the last day at 23:30
        still = alive & ~closed
        end_pre = bal + credit - debit
        rate = P.CASA_RATE["after" if m_end_d >= np.datetime64(P.RATE_CUT_DATE) else "before"]
        avg = (bal_start + end_pre) / 2
        interest = np.where(still, np.round(np.maximum(avg, 0) * rate / 100 * DAYS_IN_MONTH[m] / 365), 0)
        ii = np.flatnonzero(interest > 0)
        post_casa(ii, np.full(len(ii), m_start + (DAYS_IN_MONTH[m] - 1) * DAY + 23 * HOUR + 30 * MINUTE),
                  interest[ii].astype(np.int64), +1, "interest")

        bal = bal + credit - debit

    fds = pd.DataFrame(fd)
    fds["status"] = fd_status
    fds["close_date"] = np.array(fd_close, dtype="datetime64[D]")
    cust = cust.copy()
    cust["closed"] = closed
    cust["close_ts"] = close_ts
    return ledger.frame(), fds, pd.concat(card_parts, ignore_index=True), cust
