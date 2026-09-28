"""Break the data on purpose to prove each check catches it, then restore it.

For every check with a `-- break:` line, this runs the check, applies the break
inside a transaction, runs the check again, rolls the transaction back and
runs the check a third time. A check passes this test only if the break raised
its failing-row count and the rollback brought it back.

    python -m src.break_tests
"""

import time

import pandas as pd

from src.checks import load_checks, schema_mismatches
from src.config import REPORTS_DIR, connect
from src.export import powerbi_check
from src.export.dashboard_data import DATA
from src.export.powerbi_report import hex_id

REPORT = REPORTS_DIR / "break_test_report.md"
SCHEMA_BREAK = "ALTER TABLE marts.dim_channel ADD COLUMN undocumented_column INTEGER"

# Deliberate breaks of the generated Power BI report, each made to a copy of its files in memory:
# (what is broken, the file it is made in, text in that file, what it is replaced with)
REPORT_BREAKS = [
    ("Rename the measure 'CASA ratio' in the model, so the charts that plot it point at nothing",
     "tables/KPI trend.tmdl", "measure 'CASA ratio' =", "measure 'CASA ratio %' ="),
    ("Colour a series the data does not have: 'Plan' becomes 'Budget' on one chart",
     "visual.json", "\"Value\": \"'Plan'\"", "\"Value\": \"'Budget'\""),
    ("Point the Scorecard table's Power Query at a chart that is not in dashboard_data.csv",
     "tables/Scorecard.tmdl", '[chart] = "tiles"', '[chart] = "tile"'),
    ("Filter the PAR30 measure on a KPI that is not in the data",
     "tables/KPI trend.tmdl", "[KPI ID] = \"K19\"", "[KPI ID] = \"K91\""),
    ("Make a measure add up a column that does not exist",
     "tables/Vintage.tmdl", "SUM(Vintage[Share past due])", "SUM(Vintage[Shares past due])"),
    ("Sort the funnel's steps by a column the table does not have",
     "tables/Sign-up funnel.tmdl", "sortByColumn: 'Step order'", "sortByColumn: 'Step number'"),
    ("Leave 'Suspected fraud' out of the decline reasons' sort order",
     "tables/Card declines.tmdl", ', "Suspected fraud"}', "}"),
    ("Tell the shared read of the CSV that it has 14 columns, not 15",
     "expressions.tmdl", "Columns = 15", "Columns = 14"),
    ("Rename the KPI trend table's Definition column to Actual, which holds unique values in the scorecard, "
     "so Power BI would link the two tables", "tables/KPI trend.tmdl", "\tcolumn Definition\n", "\tcolumn Actual\n"),
    ("Widen a page's header past the edge of the page", "visual.json", '"height": 64,\n    "width": 1232',
     '"height": 64,\n    "width": 1332'),
    ("Make the scorecard taller, so it overlaps the chart below it", "visual.json", '"height": 250', '"height": 300'),
    ("Drop a comma from a visual's JSON", "visual.json", '"visualType": "pivotTable",', '"visualType": "pivotTable"'),
    ("Leave the Credit page out of pages.json", "pages/pages.json", f',\n    "{hex_id("page:Credit")}"', ""),
]


def broken_copy(files, where, text, replacement):
    for rel in sorted(files):
        if rel.endswith(where) and text in files[rel]:
            return {**files, rel: files[rel].replace(text, replacement, 1)}
    raise SystemExit(f"Break-test setup: {text!r} is not in any {where} of the Power BI report")


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

    data = pd.read_csv(DATA, dtype={"month": str})
    clean = powerbi_check.read_files()
    for description, where, text, replacement in REPORT_BREAKS:
        before = len(powerbi_check.problems(clean, data))
        broken = len(powerbi_check.problems(broken_copy(clean, where, text, replacement), data))
        after = len(powerbi_check.problems(powerbi_check.read_files(), data))
        rows.append(("powerbi_report_check", "error", description, before, broken, after))

    ok = True
    lines = [
        "# Break-test report",
        "",
        "Each check is run on the clean warehouse, again after breaking the data on purpose inside a "
        "transaction, and a third time after rolling the break back. The Power BI report check is tested the "
        "same way on broken copies of the report's files, made in memory; its counts are the problems it "
        "reports rather than rows. Written by `python -m src.break_tests`.",
        "",
        "| Check | Severity | How it was broken | Rows before | After break | After restore | Result |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for name, severity, brk, b, x, a in rows:
        caught = x > b and a == b
        ok &= caught
        result = "caught and restored" if caught else "NOT CAUGHT"
        how = brk if name == "powerbi_report_check" else f"`{brk}`"
        lines.append(f"| `{name}` | {severity} | {how} | {b:,} | {x:,} | {a:,} | {result} |")
        print(f"      {'OK ' if caught else 'BAD'} {name:<34} {b:>6,} -> {x:>6,} -> {a:>6,}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"      {sum(1 for r in rows if r[4] > r[3] and r[5] == r[3])} of {len(rows)} checks caught their break "
          f"({time.perf_counter() - started:.1f} s)")
    if not ok:
        raise SystemExit("At least one check did not catch its deliberate break; see reports/break_test_report.md")


if __name__ == "__main__":
    main()
