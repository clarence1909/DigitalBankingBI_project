"""Break the data on purpose to prove each check catches it, then restore it.

For every check with a `-- break:` line, this runs the check, applies the break
inside a transaction, runs the check again, rolls the transaction back and
runs the check a third time. A check passes this test only if the break raised
its failing-row count and the rollback brought it back.

    python -m src.break_tests
"""

import time

from src.checks import load_checks, schema_mismatches
from src.config import REPORTS_DIR, connect

REPORT = REPORTS_DIR / "break_test_report.md"
SCHEMA_BREAK = "ALTER TABLE marts.dim_channel ADD COLUMN undocumented_column INTEGER"


def count(con, sql):
    return con.execute(f"SELECT count(*) FROM ({sql}) AS failing").fetchone()[0]


def main():
    started = time.perf_counter()
    con = connect()
    rows = []
    for c in load_checks():
        if not c["break"]:
            continue
        before = count(con, c["sql"])
        con.execute("BEGIN TRANSACTION")
        con.execute(c["break"])
        broken = count(con, c["sql"])
        con.execute("ROLLBACK")
        after = count(con, c["sql"])
        rows.append((c["name"], c["severity"], c["break"], before, broken, after))

    before = len(schema_mismatches(con))
    con.execute("BEGIN TRANSACTION")
    con.execute(SCHEMA_BREAK)
    broken = len(schema_mismatches(con))
    con.execute("ROLLBACK")
    after = len(schema_mismatches(con))
    rows.append(("schema_yml_matches_warehouse", "error", SCHEMA_BREAK, before, broken, after))
    con.close()

    ok = True
    lines = [
        "# Break-test report",
        "",
        "Each check is run on the clean warehouse, again after breaking the data on purpose inside a "
        "transaction, and a third time after rolling the break back. Written by `python -m src.break_tests`.",
        "",
        "| Check | Severity | How the data was broken | Rows before | After break | After restore | Result |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for name, severity, brk, b, x, a in rows:
        caught = x > b and a == b
        ok &= caught
        result = "caught and restored" if caught else "NOT CAUGHT"
        lines.append(f"| `{name}` | {severity} | `{brk}` | {b:,} | {x:,} | {a:,} | {result} |")
        print(f"      {'OK ' if caught else 'BAD'} {name:<34} {b:>6,} -> {x:>6,} -> {a:>6,}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"      {sum(1 for r in rows if r[4] > r[3] and r[5] == r[3])} of {len(rows)} checks caught their break "
          f"({time.perf_counter() - started:.1f} s)")
    if not ok:
        raise SystemExit("At least one check did not catch its deliberate break; see reports/break_test_report.md")


if __name__ == "__main__":
    main()
