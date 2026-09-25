"""Stage 5 of the pipeline: everything a reader sees, built from the warehouse.

  1. the five analyses: charts and reports/findings.json
  2. the Executive page picture for the README
  3. tidy CSV extracts for the Tableau dashboard
  4. the Excel KPI pack, then its recalculation check against the warehouse
  5. the data dictionary, ER diagram and KPI dictionary
  6. the insights report, and the headline findings in the README
"""

from src import analysis, docs, report
from src.config import ROOT, connect
from src.export import excel_check, excel_pack, executive_page, tableau


def main():
    con = connect(read_only=True)
    print("      Analyses")
    findings = analysis.run_all(con)

    executive = executive_page.run(con)
    executive["chart"] = executive["chart"].relative_to(ROOT).as_posix()
    print(f"      Executive page  {executive['chart']}")

    written = tableau.export(con)
    print(f"      Dashboard extracts: {len(written)} files, {sum(n for _, n in written):,} rows in "
          f"{written[0][0].parent.relative_to(ROOT).as_posix()}/")

    pack = excel_pack.build(con)
    print(f"      Excel KPI pack  {pack.relative_to(ROOT).as_posix()}")
    excel_summary = excel_check.run(con)

    for path in docs.generate(con):
        print(f"      Generated       {path.relative_to(ROOT).as_posix()}")
    path = report.write(con, findings, executive, excel_summary)
    print(f"      Insights report {path.relative_to(ROOT).as_posix()}; README headline findings updated")
    con.close()
