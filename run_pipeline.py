"""Rebuild the Kelip Bank BI project from raw files with one command.

    python run_pipeline.py

The stages run in order: generate, load, model, check, publish. Each stage is
filled in during the build; until then it says which phase adds it.

All data is synthetic. Kelip Bank is a fictional Malaysian digital bank.
"""

import importlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Pipeline outputs. Both stay out of Git (see .gitignore).
RAW_DIR = ROOT / "data" / "raw"
WAREHOUSE = ROOT / "data" / "warehouse" / "kelip_bank.duckdb"

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
    print("      Not built yet (P2)")


def load() -> None:
    """Load every source into DuckDB as text and log the row counts."""
    print("      Not built yet (P2)")


def model() -> None:
    """Build the staging, mart and KPI layers from sql/."""
    print("      Not built yet (P3 and P4)")


def check() -> None:
    """Run the data quality checks and reconciliations in sql/tests/."""
    print("      Not built yet (P4)")


def publish() -> None:
    """Export the Tableau extracts, charts and the Excel KPI pack."""
    print("      Not built yet (P5 and P6)")


STAGES = [generate, load, model, check, publish]


def main() -> None:
    started = time.perf_counter()
    print("Kelip Bank BI pipeline (all data is synthetic)\n")
    check_environment()

    for number, stage in enumerate(STAGES, start=1):
        print(f"\n[{number}/{len(STAGES)}] {stage.__name__}: {stage.__doc__}")
        stage()

    print(f"\nFinished in {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
