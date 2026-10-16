"""Write the simulation out as six source systems in four formats, plus samples."""

import gzip
import io

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from src.config import DATA_END, RAW_DIR, SAMPLE_DIR

from . import params as P
from .mess import (CARD_STATUS_VARIANTS, EMPLOYMENT_VARIANTS, ENTRY_MODE_VARIANTS, ONLINE_MCCS,
                   PRODUCT_CODE_VARIANTS, STATE_VARIANTS, pick_variants, txn_code_for)
from .timeutil import (DAY, END_TS, HOUR, SECOND, month_index, to_utc)

SAMPLE_ROWS = 200

# The files each source system delivers
SOURCE_FILES = {
    "app_events": "app_events.json.gz",
    "customers": "customers.csv",
    "accounts": "accounts.csv",
    "account_balances": "account_balances.csv.gz",
    "ledger_postings": "ledger_postings.parquet",
    "card_authorisations": "card_authorisations.csv.gz",
    "loans": "loans.parquet",
    "loan_tape": "loan_tape.parquet",
    "marketing_spend": "marketing_spend.xlsx",
}


def _gzip_bytes(data: bytes, path):
    # mtime=0 keeps the file byte-identical between runs
    with open(path, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, compresslevel=5) as gz:
        gz.write(data)


def _csv(df, path):
    """Write a CSV with Arrow's writer (quotes only where needed, empty for nulls)."""
    buf = io.BytesIO()
    table = pa.Table.from_pandas(df.reset_index(drop=True), preserve_index=False)
    pacsv.write_csv(table, buf)
    data = buf.getvalue()
    if str(path).endswith(".gz"):
        _gzip_bytes(data, path)
    else:
        path.write_bytes(data)


def make_ids(prefix, numbers, width):
    """Vectorised ids such as LP0000000001, via Arrow string kernels."""
    s = pc.utf8_lpad(pc.cast(pa.array(np.asarray(numbers, dtype=np.int64)), pa.string()), width=width, padding="0")
    return np.asarray(pc.binary_join_element_wise(prefix, s, "").to_numpy(zero_copy_only=False), dtype=object)


def _utc_str(ts_myt, unit="s"):
    return np.datetime_as_string(to_utc(ts_myt), unit=unit)


def _money(sen_values):
    """Integer sen to an exact 2-decimal string such as 1234.05 (Arrow kernels, so fast)."""
    s = np.asarray(sen_values, dtype=np.int64)
    a = np.abs(s)
    whole = pc.cast(pa.array(a // 100), pa.string())
    frac = pc.utf8_lpad(pc.cast(pa.array(a % 100), pa.string()), width=2, padding="0")
    sign = pa.array(np.where(s < 0, "-", ""))
    # the last argument is the separator placed between the others
    out = pc.binary_join_element_wise(pc.binary_join_element_wise(sign, whole, ""), frac, ".")
    return np.asarray(out.to_numpy(zero_copy_only=False), dtype=object)


def write_app_events(lines):
    _gzip_bytes(("\n".join(lines) + "\n").encode("utf-8"), RAW_DIR / SOURCE_FILES["app_events"])
    (SAMPLE_DIR / "app_events_sample.json").write_text("\n".join(lines[:SAMPLE_ROWS]) + "\n", encoding="utf-8")


def write_customers(rng, cust):
    n = len(cust)
    open_d = cust["open_ts"].to_numpy(dtype="datetime64[s]").astype("datetime64[D]")
    income = cust["income"].to_numpy()
    band = np.select([income < 2000, income < 4000, income < 6000, income < 10000],
                     ["<2k", "2k-4k", "4k-6k", "6k-10k"], ">10k")
    flag = cust["fraud_flag_date"].to_numpy(dtype="datetime64[D]")
    df = pd.DataFrame({
        "customer_id": cust["customer_id"],
        "applicant_id": cust["applicant_id"],
        "open_date": pd.to_datetime(open_d).strftime("%d/%m/%Y"),      # core banking uses DD/MM/YYYY
        "birth_year": cust["birth_year"],
        "state": pick_variants(rng, cust["state"].to_numpy(), STATE_VARIANTS),
        "employment_type": pick_variants(rng, cust["employment"].to_numpy(), EMPLOYMENT_VARIANTS),
        "monthly_income_band": band,
        "risk_rating": cust["risk_rating"],
        "fraud_flag_date": np.where(np.isnat(flag), "", pd.to_datetime(flag).strftime("%d/%m/%Y")),
        "customer_status": np.where(cust["closed"], "CLOSED", "ACTIVE"),
        "last_updated_at": _utc_str(cust["open_ts"].to_numpy(dtype="datetime64[s]") + HOUR),
    })
    # Mess: a re-extract left some customers in the file twice, the later row
    # carrying a reviewed risk rating
    dup = rng.random(n) < 0.003
    again = df[dup].copy()
    again["risk_rating"] = np.where(again["risk_rating"] == "low", "medium", "high")
    later = cust["open_ts"].to_numpy(dtype="datetime64[s]")[dup] + rng.integers(20, 200, dup.sum()) * DAY
    again["last_updated_at"] = _utc_str(np.minimum(later, END_TS))
    df = pd.concat([df, again]).sort_values(["customer_id", "last_updated_at"], kind="stable")
    _csv(df, RAW_DIR / SOURCE_FILES["customers"])
    _csv(df.head(SAMPLE_ROWS), SAMPLE_DIR / "customers_sample.csv")


def build_accounts(rng, cust, fds):
    open_d = cust["open_ts"].to_numpy(dtype="datetime64[s]").astype("datetime64[D]")
    close_d = cust["close_ts"].to_numpy(dtype="datetime64[s]").astype("datetime64[D]")
    casa = pd.DataFrame({
        "account_id": cust["casa_id"], "customer_id": cust["customer_id"], "product_std": "SAV-01",
        "open_date": open_d, "close_date": close_d,
        "account_status": np.where(cust["closed"], "CLOSED", "ACTIVE"),
        "interest_rate_pct": P.CASA_RATE["after"], "principal": None, "tenor_months": None,
        "maturity_date": np.datetime64("NaT"), "campaign_code": None, "rollover_of_account_id": None,
        "linked_account_id": None, "activation_date": np.datetime64("NaT"),
    })
    fd_ids = np.array([f"FD{i + 1:08d}" for i in range(len(fds))], dtype=object)
    roll = fds["rollover_of"].to_numpy()
    fda = pd.DataFrame({
        "account_id": fd_ids,
        "customer_id": cust["customer_id"].to_numpy()[fds["cust"].to_numpy()],
        "product_std": fds["product"],
        "open_date": fds["open_ts"].to_numpy(dtype="datetime64[s]").astype("datetime64[D]"),
        "close_date": fds["close_date"].to_numpy(dtype="datetime64[D]"),
        "account_status": fds["status"],
        "interest_rate_pct": fds["rate"],
        "principal": _money(fds["principal"].to_numpy()),
        "tenor_months": fds["tenor"],
        "maturity_date": fds["maturity"].to_numpy(dtype="datetime64[D]"),
        "campaign_code": np.where(fds["promo"], P.PROMO_CODE, None),
        "rollover_of_account_id": np.where(roll >= 0, [f"FD{j + 1:08d}" for j in roll], None),
        "linked_account_id": cust["casa_id"].to_numpy()[fds["cust"].to_numpy()],
        "activation_date": np.datetime64("NaT"),
    })
    has_card = cust["card_issued"].to_numpy()
    cc = cust[has_card]
    act = cc["card_act_ts"].to_numpy(dtype="datetime64[s]").astype("datetime64[D]")
    card = pd.DataFrame({
        "account_id": cc["card_id"], "customer_id": cc["customer_id"], "product_std": "DC-01",
        "open_date": open_d[has_card], "close_date": close_d[has_card],
        "account_status": np.where(cc["closed"], "CLOSED", np.where(np.isnat(act), "NOT_ACTIVATED", "ACTIVE")),
        "interest_rate_pct": None, "principal": None, "tenor_months": None,
        "maturity_date": np.datetime64("NaT"), "campaign_code": None, "rollover_of_account_id": None,
        "linked_account_id": cc["casa_id"], "activation_date": act,
    })
    acc = pd.concat([casa, fda, card], ignore_index=True)
    return acc


def write_accounts(rng, acc):
    out = acc.copy()
    out.insert(2, "product_code", pick_variants(rng, out.pop("product_std").to_numpy(), PRODUCT_CODE_VARIANTS,
                                                dominant=0.85))
    for col in ["open_date", "close_date", "maturity_date", "activation_date"]:
        d = out[col].to_numpy(dtype="datetime64[D]")
        out[col] = np.where(np.isnat(d), "", np.datetime_as_string(d, unit="D"))
    out = out.sort_values(["open_date", "account_id"], kind="stable")
    _csv(out, RAW_DIR / SOURCE_FILES["accounts"])
    _csv(out.head(SAMPLE_ROWS), SAMPLE_DIR / "accounts_sample.csv")


def ledger_frame(rng, led, cust, auth_id_by_key, n_fd):
    """Postings with account ids, UTC timestamps and the posting engine's codes."""
    from .banking import TXN_TYPES

    is_fd = led["is_fd"].to_numpy()
    idx = led["idx"].to_numpy()
    ts = led["ts"].to_numpy(dtype="datetime64[s]")
    txn = led["txn"].to_numpy()
    amount = led["amount"].to_numpy()
    # Stable, deterministic order: time, account, transaction type, amount
    acct_key = np.where(is_fd, 10_000_000 + idx, idx)
    order = np.lexsort((amount, txn, acct_key, ts.astype(np.int64)))
    is_fd, idx, ts, txn, amount = is_fd[order], idx[order], ts[order], txn[order], amount[order]
    sign = led["sign"].to_numpy()[order]
    ref = led["ref"].to_numpy(dtype=object)[order].copy()

    casa_ids = cust["casa_id"].to_numpy(dtype=object)
    fd_ids = make_ids("FD", np.arange(1, n_fd + 1), 8)
    acct = np.where(is_fd, fd_ids[np.where(is_fd, idx, 0)], casa_ids[np.where(is_fd, 0, idx)])
    card = TXN_TYPES.index("card_purchase")
    is_card = txn == card
    ref[is_card] = pd.Series(ref[is_card], dtype=object).map(auth_id_by_key).to_numpy(dtype=object)
    code = np.empty(len(txn), dtype=object)
    for i, name in enumerate(TXN_TYPES):
        sel = txn == i
        if sel.any():
            code[sel] = txn_code_for(name, ts[sel])
    channel_of = {"salary": "IBG", "duitnow_in": "DUITNOW", "duitnow_out": "DUITNOW", "bill_payment": "JOMPAY",
                  "card_purchase": "CARD", "interest": "SYSTEM"}
    channel = np.array([channel_of.get(name, "INTERNAL") for name in TXN_TYPES], dtype=object)[txn]
    return pd.DataFrame({
        "posting_id": make_ids("LP", np.arange(1, len(txn) + 1), 10),
        "account_id": acct, "posting_ts_myt": ts, "amount_sen": amount,
        "direction": np.where(sign > 0, "CR", "DR").astype(object), "txn_code": code,
        "channel": channel, "reference": ref,
    })


def _decimal(sen_values):
    """Integer sen to an exact decimal(18,2) Arrow array."""
    return pa.array(_money(sen_values)).cast(pa.decimal128(18, 2))


def write_ledger(df):
    tbl = pa.table({
        "posting_id": pa.array(df["posting_id"], pa.string()),
        "account_id": pa.array(df["account_id"], pa.string()),
        "posting_ts": pa.array(to_utc(df["posting_ts_myt"].to_numpy(dtype="datetime64[s]")),
                               pa.timestamp("us", tz="UTC")),
        "amount": _decimal(df["amount_sen"].to_numpy()),
        "direction": pa.array(df["direction"], pa.string()),
        "txn_code": pa.array(df["txn_code"], pa.string()),
        "channel": pa.array(df["channel"], pa.string()),
        "reference": pa.array(df["reference"], pa.string()),
    })
    pq.write_table(tbl, RAW_DIR / SOURCE_FILES["ledger_postings"], compression="zstd", row_group_size=500_000)
    pq.write_table(tbl.slice(0, SAMPLE_ROWS * 2), SAMPLE_DIR / "ledger_postings_sample.parquet")


def month_end_balances(post, acc):
    """Month-end balance of every savings and FD account, built from the postings (MYT months)."""
    post = post.copy()
    post["m"] = month_index(post["posting_ts_myt"].to_numpy(dtype="datetime64[s]"))
    signed = np.where(post["direction"] == "CR", post["amount_sen"], -post["amount_sen"])
    post["signed"] = signed
    flows = post.groupby(["account_id", "m"], sort=False)["signed"].sum()

    dep = acc[acc["product_std"] != "DC-01"][["account_id", "open_date", "close_date"]].copy()
    first = month_index(dep["open_date"].to_numpy(dtype="datetime64[D]"))
    close = dep["close_date"].to_numpy(dtype="datetime64[D]")
    last = month_index(np.where(np.isnat(close), np.datetime64(DATA_END), close))
    counts = last - first + 1
    grid = pd.DataFrame({
        "account_id": np.repeat(dep["account_id"].to_numpy(), counts),
        "m": np.concatenate([np.arange(a, b + 1) for a, b in zip(first, last)]),
    })
    grid["flow"] = flows.reindex(pd.MultiIndex.from_frame(grid[["account_id", "m"]])).fillna(0).to_numpy(np.int64)
    grid["balance_sen"] = grid.groupby("account_id", sort=False)["flow"].cumsum()
    return grid


def write_balances(bal):
    from .timeutil import MONTH_END_DATE
    out = pd.DataFrame({
        "account_id": bal["account_id"],
        "balance_date": np.datetime_as_string(MONTH_END_DATE[bal["m"].to_numpy()], unit="D"),
        "ledger_balance": _money(bal["balance_sen"].to_numpy()),
        "currency": "MYR",
    })
    out = out.sort_values(["balance_date", "account_id"], kind="stable")
    _csv(out, RAW_DIR / SOURCE_FILES["account_balances"])
    _csv(out.head(SAMPLE_ROWS), SAMPLE_DIR / "account_balances_sample.csv")


def _arrow_str(values):
    return pa.array(np.asarray(values, dtype=object), pa.string())


def _to_obj(arrow_array):
    return np.asarray(arrow_array.to_numpy(zero_copy_only=False), dtype=object)


def card_frame(rng, cards, cust):
    """Card processor records: one per authorisation, plus status updates and resends."""
    order = np.lexsort((cards["amount_sen"].to_numpy(), cards["cust"].to_numpy(),
                        cards["auth_ts"].to_numpy(dtype="datetime64[s]").astype(np.int64)))
    cards = cards.iloc[order].reset_index(drop=True)
    n = len(cards)
    auth_id = make_ids("AU", np.arange(1, n + 1), 10)
    mcc = cards["mcc"].to_numpy()
    label_of = {m[0]: m[1] for m in P.MERCHANTS}
    base = _arrow_str([label_of[x] for x in mcc])
    case = rng.random(n)
    label = np.where(case < 0.6, _to_obj(base),
                     np.where(case < 0.85, _to_obj(pc.utf8_upper(base)), _to_obj(pc.utf8_lower(base))))
    mode_std = np.where(np.isin(mcc, list(ONLINE_MCCS)), "ECOM",
                        np.where(rng.random(n) < 0.7, "CONTACTLESS", "CHIP"))
    auth_ts = cards["auth_ts"].to_numpy(dtype="datetime64[s]")
    settle = cards["settle"].to_numpy(dtype="datetime64[D]")
    status_std = cards["status"].to_numpy(dtype=object)
    settle_str = _to_obj(pc.replace_substring(_arrow_str(np.datetime_as_string(settle, unit="D")), "-", ""))
    df = pd.DataFrame({
        "auth_id": auth_id,
        "card_id": cust["card_id"].to_numpy(dtype=object)[cards["cust"].to_numpy()],
        "auth_ts": _to_obj(pc.replace_substring(_arrow_str(_utc_str(auth_ts)), "T", " ")),
        "amount": _money(cards["amount_sen"].to_numpy()),
        "currency": "MYR",
        "mcc": mcc,
        "merchant_category": label,
        "entry_mode": pick_variants(rng, mode_std, ENTRY_MODE_VARIANTS, dominant=0.8),
        "response_code": cards["response_code"].to_numpy(dtype=object),
        "status": np.where(status_std == "REVERSED", "APPROVED", status_std).astype(object),
        "settlement_date": np.where(np.isnat(settle), "", settle_str).astype(object),
        "record_updated_at": _utc_str(np.where(np.isnat(settle), auth_ts + 5 * SECOND,
                                               settle.astype("datetime64[s]") + 5 * HOUR)).astype(object),
    })
    upd_ts = np.where(np.isnat(settle), auth_ts + 5 * SECOND, settle.astype("datetime64[s]") + 5 * HOUR)
    df["_n"] = np.arange(n)
    df["_upd"] = upd_ts.astype(np.int64)
    # Reversals arrive as a second record with the new status
    rev = status_std == "REVERSED"
    upd = df[rev].copy()
    upd["status"] = "REVERSED"
    rev_ts = np.minimum(auth_ts[rev] + rng.integers(1, 48, rev.sum()) * HOUR, END_TS)
    upd["record_updated_at"] = _utc_str(rev_ts).astype(object)
    upd["_upd"] = rev_ts.astype(np.int64)
    # Resends: the processor sometimes sends the same record twice (reversed ones resend as reversed)
    resend = (rng.random(n) < P.P_PROCESSOR_RESEND) & ~rev
    again = df[resend].copy()
    again_ts = np.minimum(upd_ts[resend] + DAY, END_TS)
    again["record_updated_at"] = _utc_str(again_ts).astype(object)
    again["_upd"] = again_ts.astype(np.int64)
    out = pd.concat([df, upd, again], ignore_index=True)
    out["status"] = pick_variants(rng, out["status"].to_numpy(dtype=object), CARD_STATUS_VARIANTS, dominant=0.85)
    out = out.iloc[np.lexsort((out["_n"].to_numpy(), out["_upd"].to_numpy()))].drop(columns=["_n", "_upd"])
    auth_id_by_key = dict(zip(cards["auth_key"].to_numpy(dtype=object), auth_id))
    return out, auth_id_by_key


def write_cards(out):
    _csv(out, RAW_DIR / SOURCE_FILES["card_authorisations"])
    _csv(out.head(SAMPLE_ROWS), SAMPLE_DIR / "card_authorisations_sample.csv")


def write_loans(loans, tape, cust):
    def dec(values):
        return _decimal(np.round(np.asarray(values, dtype=float) * 100).astype(np.int64))

    lt = pa.table({
        "loan_id": pa.array(loans["loan_id"], pa.string()),
        "customer_id": pa.array(cust["customer_id"].to_numpy()[loans["customer_idx"].to_numpy()], pa.string()),
        "application_date": pa.array(loans["application_date"].to_numpy(dtype="datetime64[D]"), pa.date32()),
        "disbursement_date": pa.array(loans["disb_ts"].to_numpy(dtype="datetime64[s]").astype("datetime64[D]"),
                                      pa.date32()),
        "principal": dec(loans["principal"]),
        "tenor_months": pa.array(loans["tenor_months"], pa.int32()),
        "interest_rate_pct": dec(loans["rate_pct"]),
        "risk_grade": pa.array(loans["grade"], pa.string()),
        "credit_policy_code": pa.array(loans["policy"], pa.string()),
        "dsr_pct": dec(loans["dsr_pct"]),
    })
    pq.write_table(lt, RAW_DIR / SOURCE_FILES["loans"], compression="zstd")
    pq.write_table(lt.slice(0, SAMPLE_ROWS), SAMPLE_DIR / "loans_sample.parquet")
    tape = tape.sort_values(["snapshot_date", "loan"], kind="stable")
    tt = pa.table({
        "loan_id": pa.array(loans["loan_id"].to_numpy()[tape["loan"].to_numpy()], pa.string()),
        "snapshot_date": pa.array(tape["snapshot_date"].to_numpy(dtype="datetime64[D]"), pa.date32()),
        "outstanding_principal": dec(tape["outstanding_principal"]),
        "instalments_due": pa.array(tape["instalments_due"], pa.int32()),
        "instalments_paid": pa.array(tape["instalments_paid"], pa.int32()),
        "days_past_due": pa.array(tape["days_past_due"], pa.int32()),
        "loan_status": pa.array(tape["loan_status"], pa.string()),
    })
    pq.write_table(tt, RAW_DIR / SOURCE_FILES["loan_tape"], compression="zstd")
    pq.write_table(tt.slice(0, SAMPLE_ROWS), SAMPLE_DIR / "loan_tape_sample.parquet")
