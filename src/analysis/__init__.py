"""The five analyses (P5). Each returns one chart titled with its takeaway and a three-line finding."""

from src.config import ROOT

from . import acquisition, common, credit, deposits, onboarding, segments

ANALYSES = [acquisition, onboarding, deposits, credit, segments]


def run_all(con):
    findings = {}
    for module in ANALYSES:
        result = module.run(con)
        result["chart"] = result["chart"].relative_to(ROOT).as_posix()
        findings[result["id"]] = result
        print(f"      {result['id']:<12} {result['chart']}")
    common.write_findings(findings)
    return findings
