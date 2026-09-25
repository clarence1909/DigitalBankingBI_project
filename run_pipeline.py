"""Rebuild the Kelip Bank BI project from raw files with one command.

    python run_pipeline.py                 # everything
    python run_pipeline.py --from model    # skip regenerating and reloading the data
    python run_pipeline.py --only check    # one stage

The stages run in order: generate, load, model, check, publish.

All data is synthetic. Kelip Bank is a fictional Malaysian digital bank.
"""

import argparse
import importlib
import sys
import time

MIN_PYTHON = (3, 11)

# Import name -> package name in requirements.txt
PACKAGES = {
    "duckdb": "duckdb",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "sklearn": "scikit-learn",
    "scipy": "scipy",
    "yaml": "pyyaml",
}


def check_environment() -> None:
    """Stop straight away, with the fix, if Python or a package is missing."""
    if sys.version_info < MIN_PYTHON:
        sys.exit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is needed "
            f"(this is {sys.version.split()[0]})."
        )

    missing = []
    for module, package in PACKAGES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        sys.exit(
            "Missing packages: " + ", ".join(missing)
            + "\nInstall them with: pip install -r requirements.txt"
        )

    print(f"Python {sys.version.split()[0]}, all {len(PACKAGES)} packages found")


def generate() -> None:
    """Simulate 24 months of the six source systems into data/raw/."""
    from src.generate import simulate
    simulate.main()


def load() -> None:
    """Load every source into DuckDB as text and log the row counts."""
    from src import load as loader
    loader.main()


def model() -> None:
    """Build the staging, mart and KPI layers from sql/."""
    from src import model as modeller
    modeller.main()


def check() -> None:
    """Run the data quality checks, reconciliations and ad-hoc queries."""
    from src import checks
    checks.main()


def publish() -> None:
    """Run the analyses, then export the Tableau extracts, Excel KPI pack and docs."""
    from src import publish as publisher
    publisher.main()


STAGES = [generate, load, model, check, publish]
STAGE_NAMES = [s.__name__ for s in STAGES]


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the Kelip Bank BI project.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--from", dest="start", choices=STAGE_NAMES, help="start at this stage")
    group.add_argument("--only", choices=STAGE_NAMES, help="run just this stage")
    args = parser.parse_args()

    if args.only:
        selected = [s for s in STAGES if s.__name__ == args.only]
    elif args.start:
        selected = STAGES[STAGE_NAMES.index(args.start):]
    else:
        selected = STAGES

    started = time.perf_counter()
    print("Kelip Bank BI pipeline (all data is synthetic)\n")
    check_environment()

    for stage in selected:
        number = STAGE_NAMES.index(stage.__name__) + 1
        print(f"\n[{number}/{len(STAGES)}] {stage.__name__}: {stage.__doc__}")
        stage_started = time.perf_counter()
        stage()
        print(f"      done in {time.perf_counter() - stage_started:.1f} s")

    print(f"\nFinished in {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
