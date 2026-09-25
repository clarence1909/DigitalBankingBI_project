"""Stage 1 of the pipeline: simulate Kelip Bank and write the six source systems.

Everything is driven by one seed, split into independent random streams, so a
clean run always writes the same files.
"""

import shutil
import time

import numpy as np

from src.config import RAW_DIR, SAMPLE_DIR, SEED

from .banking import build_customers, simulate_banking
from .loans import simulate_loans
from .marketing import spend_table, write_sheet
from .onboarding import build_events, events_to_json_lines, simulate_applicants
from .timeutil import N_MONTHS, month_index
from .writers import (SOURCE_FILES, build_accounts, card_frame, ledger_frame, month_end_balances,
                      write_accounts, write_app_events, write_balances, write_cards, write_customers,
                      write_ledger, write_loans)


def _counts_by_month(ts, groups, index):
    import pandas as pd

    df = pd.DataFrame({"m": month_index(ts), "g": groups})
    return (df.groupby(["m", "g"]).size().unstack(fill_value=0)
            .reindex(index=range(N_MONTHS), columns=index, fill_value=0))


def main():
    # Plain Python strings are much quicker than Arrow strings for building these tables
    import pandas as pd

    with pd.option_context("future.infer_string", False):
        _generate()


def _generate():
    started = time.perf_counter()
    for d in (RAW_DIR, SAMPLE_DIR):
        d.mkdir(parents=True, exist_ok=True)
    for f in RAW_DIR.glob("*"):
        if f.name != ".gitkeep":
            f.unlink()

    streams = np.random.SeedSequence(SEED).spawn(7)
    r_app, r_evt, r_cust, r_loan, r_bank, r_out, r_mkt = (np.random.default_rng(s) for s in streams)

    app = simulate_applicants(r_app)
    cust = build_customers(r_cust, app)
    cust["customer_idx"] = np.arange(len(cust))
    loans, tape, loan_cash = simulate_loans(r_loan, cust)
    ledger, fds, cards, cust = simulate_banking(r_bank, cust, loans, loan_cash)

    # Source 1: the mobile app's event stream
    events = build_events(r_evt, app, dict(zip(cust["applicant_id"], cust["customer_id"])))
    write_app_events(events_to_json_lines(events))

    # Source 2: core banking (customers, accounts, month-end balances)
    write_customers(r_out, cust)
    accounts = build_accounts(r_out, cust, fds)
    write_accounts(r_out, accounts)

    # Source 4: card processor; source 3: the ledger, which references card authorisations
    card_records, auth_id_by_key = card_frame(r_out, cards, cust)
    write_cards(card_records)
    postings = ledger_frame(r_out, ledger, cust, auth_id_by_key, len(fds))
    write_ledger(postings)
    balances = month_end_balances(postings, accounts)
    if (balances["balance_sen"] < 0).any():
        raise RuntimeError("The simulation produced a negative month-end balance")
    write_balances(balances)

    # Source 5: the loan management system
    write_loans(loans, tape, cust)

    # Source 6: the marketing team's spreadsheet
    from .params import CHANNELS
    starts = _counts_by_month(app["start_ts"].to_numpy(dtype="datetime64[s]"), app["channel"], CHANNELS)
    opened = _counts_by_month(cust["open_ts"].to_numpy(dtype="datetime64[s]"), cust["channel"], CHANNELS)
    table = spend_table(r_mkt, starts, opened)
    write_sheet(r_mkt, table, RAW_DIR / SOURCE_FILES["marketing_spend"])
    shutil.copyfile(RAW_DIR / SOURCE_FILES["marketing_spend"], SAMPLE_DIR / "marketing_spend.xlsx")

    print(f"      {len(app):,} applicants, {len(cust):,} customers, {len(postings):,} ledger postings, "
          f"{len(card_records):,} card records, {len(loans):,} loans")
    print(f"      Files written to data/raw/ in {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
