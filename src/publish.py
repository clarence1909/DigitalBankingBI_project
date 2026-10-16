"""Stage 5 of the pipeline: everything a reader sees, built from the warehouse.

  1. the five analyses: charts and reports/findings.json
  2. the Executive page picture for the README
  3. tidy CSV extracts of the KPI layer, the one table the Power BI report
     reads, the generated Power BI report, and its check
  4. the Excel KPI pack, then its recalculation check against the warehouse
  5. the data dictionary, ER diagram and KPI dictionary
  6. the insights report, and the headline findings and checks in the README
"""

from src import analysis, docs, report
from src.config import ROOT, connect
from src.export import (dashboard_data, excel_check, excel_pack, executive_page, extracts, powerbi_check,
                        powerbi_report)


def main():
    con = connect(read_only=True)
    print("      Analyses")
    findings = analysis.run_all(con)

    executive = executive_page.run(con)
    executive["chart"] = executive["chart"].relative_to(ROOT).as_posix()
    print(f"      Executive page  {executive['chart']}")

    written = extracts.export(con)
    print(f"      Dashboard extracts: {len(written)} files, {sum(n for _, n in written):,} rows in "
          f"{written[0][0].parent.relative_to(ROOT).as_posix()}/")
    data = dashboard_data.build(con)
    print(f"      Dashboard data  {dashboard_data.DATA.relative_to(ROOT).as_posix()}: {len(data):,} rows "
          f"for {data['chart'].nunique()} charts")
    project = powerbi_report.build()
    print(f"      Power BI report {project['path'].relative_to(ROOT).as_posix()}: {len(project['pages'])} pages, "
          f"{project['visuals']} visuals, {project['tables']} model tables")
    powerbi_summary = powerbi_check.run()

    pack = excel_pack.build(con)
    print(f"      Excel KPI pack  {pack.relative_to(ROOT).as_posix()}")
    excel_summary = excel_check.run(con)

    for path in docs.generate(con):
        print(f"      Generated       {path.relative_to(ROOT).as_posix()}")
    path = report.write(con, findings, executive, excel_summary, powerbi_summary)
    print(f"      Insights report {path.relative_to(ROOT).as_posix()}; README headline findings updated")
    con.close()
