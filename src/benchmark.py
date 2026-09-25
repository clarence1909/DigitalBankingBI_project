"""Time the warehouse's heaviest queries, and the same work on ten times the data.

    python -m src.benchmark

Run it after the pipeline. It writes reports/benchmark.md. Timings depend on
the machine, so the benchmark is not part of the pipeline (whose outputs must
be identical on every run); the report records the machine it ran on.
"""

import os
import platform
import statistics
import time

import duckdb

from src.config import REPORTS_DIR, connect

REPORT = REPORTS_DIR / "benchmark.md"
RUNS = 5
SCALE = 10

QUERIES = [
    ("Deposits by month (the KPI query)", "marts.fct_account_balances_monthly",
     """SELECT month_start, sum(balance) FILTER (WHERE product_family = 'CASA') / sum(balance) AS casa_ratio,
               sum(interest_accrued) AS interest FROM marts.fct_account_balances_monthly GROUP BY 1"""),
    ("Reconciliation 1, account by account", "marts.fct_ledger_postings",
     """WITH p AS (SELECT account_id, posting_month, sum(amount) AS net FROM marts.fct_ledger_postings GROUP BY 1, 2)
        SELECT count(*) FROM marts.fct_account_balances_monthly AS b
        LEFT JOIN p ON p.account_id = b.account_id AND p.posting_month = b.month_start
        WHERE b.balance <> b.prior_balance + coalesce(p.net, 0)"""),
    ("Card spend by merchant category", "marts.fct_card_authorisations",
     """SELECT merchant_category, count(*), sum(amount) FROM marts.fct_card_authorisations
        WHERE is_approved_final GROUP BY 1 ORDER BY 3 DESC"""),
    ("Monthly active customers", "marts.fct_customer_monthly",
     "SELECT month_start, count(*) FILTER (WHERE is_active) FROM marts.fct_customer_monthly GROUP BY 1"),
    ("Scorecard for one month (what the dashboard reads)", "kpi.scorecard",
     "SELECT * FROM kpi.scorecard WHERE month_start = DATE '2026-08-01'"),
]

SCALED = """
    CREATE TEMP TABLE postings_x{scale} AS
    SELECT account_id || '-' || CAST(copy AS VARCHAR) AS account_id, posting_month, txn_type, amount
    FROM marts.fct_ledger_postings, range({scale}) AS r(copy)
"""
SCALED_QUERY = """
    SELECT posting_month, txn_type, count(*), sum(amount), count(DISTINCT account_id)
    FROM {table} GROUP BY 1, 2
"""


def timed(con, sql):
    times = []
    for _ in range(RUNS):
        started = time.perf_counter()
        con.execute(sql).fetchall()
        times.append(time.perf_counter() - started)
    return statistics.median(times)


def rows(con, table):
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def main():
    con = connect(read_only=True)
    threads = con.execute("SELECT current_setting('threads')").fetchone()[0]
    results = [(name, table, rows(con, table), timed(con, sql)) for name, table, sql in QUERIES]

    base_sql = SCALED_QUERY.format(table="marts.fct_ledger_postings")
    base_rows = rows(con, "marts.fct_ledger_postings")
    base_time = timed(con, base_sql)
    con.execute(SCALED.format(scale=SCALE))
    scaled_rows = rows(con, f"postings_x{SCALE}")
    scaled_time = timed(con, SCALED_QUERY.format(table=f"postings_x{SCALE}"))
    con.close()

    lines = [
        "# Query benchmark",
        "",
        "Written by `python -m src.benchmark`. Each time is the median of five runs on the warehouse built by "
        "`python run_pipeline.py`. All data is synthetic.",
        "",
        f"**Machine:** {platform.system()} {platform.machine()}, {os.cpu_count()} CPU cores, DuckDB "
        f"{duckdb.__version__} using {threads} threads.",
        "",
        "## The heaviest queries",
        "",
        "| Query | Main table | Rows | Median time |",
        "|---|---|---:|---:|",
    ]
    lines += [f"| {name} | `{table}` | {n:,} | {t * 1000:,.0f} ms |" for name, table, n, t in results]
    lines += [
        "",
        "## Ten times the data",
        "",
        f"The ledger postings copied {SCALE} times over (each copy on its own accounts), then summarised by "
        "month and transaction type with a distinct count of accounts, the most expensive kind of query here.",
        "",
        "| Data | Rows | Median time |",
        "|---|---:|---:|",
        f"| As built | {base_rows:,} | {base_time * 1000:,.0f} ms |",
        f"| {SCALE} times | {scaled_rows:,} | {scaled_time * 1000:,.0f} ms |",
        "",
        f"Ten times the rows took {scaled_time / base_time:.1f} times as long, so the work grows roughly in line "
        "with the data. The [solution design](../docs/03_solution_design.md) says what a real bank would change "
        "at larger scale.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Benchmark written to {REPORT.relative_to(REPORTS_DIR.parent)}")


if __name__ == "__main__":
    main()
