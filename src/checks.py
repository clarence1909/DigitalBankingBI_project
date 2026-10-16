"""Stage 4 of the pipeline: data quality checks, reconciliations and ad-hoc queries.

Each check in sql/tests/ is a query that returns the rows that fail it, with a
header saying its name, severity (error, warn or info) and what it tests. An
error-level failure stops the pipeline; warnings are reported but do not block;
info checks just report numbers worth knowing.
"""

import re
import time
from pathlib import Path

import pandas as pd
import yaml

from src.config import ADHOC_RESULTS_DIR, REPORTS_DIR, SCHEMA_YML, SQL_DIR, connect

TESTS_DIR = SQL_DIR / "tests"
ADHOC_DIR = SQL_DIR / "adhoc"
REPORT = REPORTS_DIR / "data_quality_report.md"
HEADER = re.compile(r"^--\s*(name|severity|description|break):\s*(.*)$")


def load_checks():
    """Read every check file: its header fields and the query itself."""
    checks = []
    for f in sorted(TESTS_DIR.glob("*.sql")):
        meta, body = {}, []
        for line in f.read_text(encoding="utf-8").splitlines():
            m = HEADER.match(line)
            if m and not body:
                meta[m.group(1)] = m.group(2).strip()
            else:
                body.append(line)
        sql = "\n".join(body).strip().rstrip(";")
        checks.append({"file": f.name, "name": meta["name"], "severity": meta["severity"],
                       "description": meta["description"], "break": meta.get("break"), "sql": sql})
    return checks


def schema_mismatches(con):
    """Compare sql/schema.yml with the tables and columns in the warehouse."""
    spec = yaml.safe_load(SCHEMA_YML.read_text(encoding="utf-8"))
    documented = set()
    for schema, s in spec["schemas"].items():
        for table, t in s["tables"].items():
            for column in t["columns"]:
                documented.add((schema, table, column))
    schemas = list(spec["schemas"])
    placeholders = ", ".join("?" for _ in schemas)
    actual = set(con.execute(
        f"SELECT table_schema, table_name, column_name FROM information_schema.columns "
        f"WHERE table_schema IN ({placeholders})", schemas).fetchall())
    rows = [(s, t, c, "in the warehouse but not in schema.yml") for s, t, c in sorted(actual - documented)]
    rows += [(s, t, c, "in schema.yml but not in the warehouse") for s, t, c in sorted(documented - actual)]
    return pd.DataFrame(rows, columns=["schema", "table", "column", "issue"])


def run_check(con, check):
    count = con.execute(f"SELECT count(*) FROM ({check['sql']}) AS failing").fetchone()[0]
    sample = con.execute(f"SELECT * FROM ({check['sql']}) AS failing LIMIT 5").df()
    return count, sample


def status_of(severity, count):
    if severity == "info":
        return "INFO"
    if count == 0:
        return "PASS"
    return "FAIL" if severity == "error" else "WARN"


def _md_table(df, max_rows=12):
    if df is None or df.empty:
        return "_No rows._\n"
    df = df.head(max_rows).copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:,.2f}")
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            # Dates at midnight read better without the time
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else
                              (f"{v:%Y-%m-%d}" if v == v.normalize() else f"{v:%Y-%m-%d %H:%M:%S}"))
        else:
            df[c] = df[c].map(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
    head = "| " + " | ".join(df.columns) + " |\n|" + "|".join("---" for _ in df.columns) + "|\n"
    return head + "".join("| " + " | ".join(r) + " |\n" for r in df.astype(str).itertuples(index=False, name=None))


def reconciliation_summaries(con):
    """Monthly tie-out tables, kept in the dq schema and shown in the report."""
    con.execute("""
        CREATE OR REPLACE TABLE dq.recon_deposits_monthly AS
        WITH b AS (
            SELECT month_start, sum(prior_balance) AS opening_balance, sum(balance) AS closing_balance
            FROM marts.fct_account_balances_monthly GROUP BY 1
        ),
        p AS (
            SELECT posting_month AS month_start, sum(amount) AS net_postings
            FROM marts.fct_ledger_postings WHERE product_family IN ('CASA', 'FD') GROUP BY 1
        )
        SELECT b.month_start, b.opening_balance, p.net_postings, b.closing_balance,
               b.opening_balance + p.net_postings - b.closing_balance AS difference
        FROM b JOIN p USING (month_start)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE dq.recon_cards_monthly AS
        WITH settled AS (
            SELECT settlement_month AS month_start, sum(amount) AS processor_settled
            FROM marts.fct_card_authorisations
            WHERE status = 'APPROVED' AND settlement_date IS NOT NULL GROUP BY 1
        ),
        by_auth AS (
            SELECT auth_month AS month_start, sum(amount) AS approved_by_auth_month
            FROM marts.fct_card_authorisations
            WHERE status = 'APPROVED' AND settlement_date IS NOT NULL GROUP BY 1
        ),
        ledger AS (
            SELECT posting_month AS month_start, -sum(amount) AS ledger_card_postings
            FROM marts.fct_ledger_postings WHERE txn_type = 'card_purchase' GROUP BY 1
        )
        SELECT s.month_start, s.processor_settled, l.ledger_card_postings,
               s.processor_settled - l.ledger_card_postings AS difference,
               a.approved_by_auth_month,
               a.approved_by_auth_month - l.ledger_card_postings AS timing_difference_if_compared_by_auth_month
        FROM settled AS s JOIN ledger AS l USING (month_start) JOIN by_auth AS a USING (month_start)
    """)
    return (con.execute("SELECT * FROM dq.recon_deposits_monthly ORDER BY month_start").df(),
            con.execute("SELECT * FROM dq.recon_cards_monthly ORDER BY month_start").df())


def run_adhoc(con):
    ADHOC_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in sorted(ADHOC_DIR.glob("*.sql")):
        sql = f.read_text(encoding="utf-8")
        question = " ".join(l.lstrip("- ").strip() for l in sql.splitlines() if l.startswith("--"))
        df = con.execute(sql).df()
        out = ADHOC_RESULTS_DIR / f"{f.stem}.csv"
        df.to_csv(out, index=False, lineterminator="\n", float_format="%.2f")
        results.append((f.name, question, len(df), out))
    return results


def main():
    started = time.perf_counter()
    con = connect()
    checks = load_checks()
    rows, details = [], []
    for c in checks:
        count, sample = run_check(con, c)
        status = status_of(c["severity"], count)
        rows.append((c["name"], c["severity"], status, count, c["description"], f"sql/tests/{c['file']}"))
        if status in ("FAIL", "WARN", "INFO"):
            details.append((c, status, count, sample))
        print(f"      {status:<5} {c['name']:<34} {count:>8,} rows")

    schema = schema_mismatches(con)
    schema_status = status_of("error", len(schema))
    desc = "sql/schema.yml describes exactly the tables and columns in the marts and kpi schemas."
    rows.append(("schema_yml_matches_warehouse", "error", schema_status, len(schema), desc, "src/checks.py"))
    if schema_status != "PASS":
        details.append(({"name": "schema_yml_matches_warehouse", "description": desc}, schema_status,
                        len(schema), schema.head(5)))
    print(f"      {schema_status:<5} {'schema_yml_matches_warehouse':<34} {len(schema):>8,} rows")

    results = pd.DataFrame(rows, columns=["check_name", "severity", "status", "failing_rows", "description",
                                          "defined_in"])
    con.register("results_df", results)
    con.execute("CREATE OR REPLACE TABLE dq.check_results AS SELECT * FROM results_df")
    con.unregister("results_df")
    deposits, cards = reconciliation_summaries(con)
    adhoc = run_adhoc(con)
    con.close()

    write_report(results, details, deposits, cards, adhoc)
    failed = results[results["status"] == "FAIL"]
    n = results["status"].value_counts()
    print(f"      {n.get('PASS', 0)} passed, {n.get('WARN', 0)} warnings, {n.get('INFO', 0)} info, "
          f"{n.get('FAIL', 0)} failed; {len(adhoc)} ad-hoc queries run ({time.perf_counter() - started:.1f} s)")
    if len(failed):
        raise SystemExit(f"Blocking data quality checks failed: {', '.join(failed['check_name'])}. "
                         f"See {REPORT.relative_to(REPORT.parents[1])}")


def write_report(results, details, deposits, cards, adhoc):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    n = results["status"].value_counts()
    lines = [
        "# Data quality report",
        "",
        "Written by `python run_pipeline.py` (check stage). All data is synthetic.",
        "",
        f"**{len(results)} checks: {n.get('PASS', 0)} passed, {n.get('WARN', 0)} warnings, "
        f"{n.get('INFO', 0)} for information, {n.get('FAIL', 0)} failed.** "
        "Errors block the pipeline; warnings and information do not.",
        "",
        "| Check | Severity | Result | Rows | What it tests |",
        "|---|---|---|---:|---|",
    ]
    for r in results.itertuples(index=False):
        lines.append(f"| `{r.check_name}` | {r.severity} | {r.status} | {r.failing_rows:,} | {r.description} |")
    lines += ["", "## Warnings and information", ""]
    for c, status, count, sample in details:
        lines += [f"### `{c['name']}` ({status}, {count:,} rows)", "", c["description"], "", _md_table(sample), ""]
    lines += [
        "## Reconciliation 1: ledger postings to month-end balances",
        "",
        "Opening balance plus the month's postings (by Malaysia-time posting date) against the closing "
        "balances core banking reports, summed over all savings and fixed deposit accounts. The check above "
        "does the same test account by account.",
        "",
        _md_table(deposits.assign(month_start=deposits["month_start"].astype(str)), max_rows=30),
        "",
        "## Reconciliation 2: card processor to ledger",
        "",
        "Settled authorisations by settlement month against card purchases posted to the ledger. Compared by "
        "authorisation month instead, late settlements create timing differences, shown in the last column; "
        "that is why the tie-out uses settlement dates.",
        "",
        _md_table(cards.assign(month_start=cards["month_start"].astype(str)), max_rows=30),
        "",
        "## Ad-hoc stakeholder queries",
        "",
        "Each query in `sql/adhoc/` runs on every build; its answer is saved as a CSV.",
        "",
    ]
    for name, question, n_rows, out in adhoc:
        lines.append(f"- `sql/adhoc/{name}`: {question} ([result]({Path('adhoc') / out.name}), {n_rows} rows)")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
