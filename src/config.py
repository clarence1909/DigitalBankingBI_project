"""Paths and settings shared by every pipeline stage."""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Data
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLE_DIR = DATA_DIR / "sample"
REFERENCE_DIR = DATA_DIR / "reference"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
WAREHOUSE = WAREHOUSE_DIR / "kelip_bank.duckdb"

# Code and outputs
SQL_DIR = ROOT / "sql"
SCHEMA_YML = SQL_DIR / "schema.yml"
REPORTS_DIR = ROOT / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"
ADHOC_RESULTS_DIR = REPORTS_DIR / "adhoc"
DASHBOARD_DIR = ROOT / "dashboards"
EXTRACTS_DIR = DASHBOARD_DIR / "extracts"
DOCS_DIR = ROOT / "docs"

# The simulation
SEED = 20240901
FIRST_MONTH = "2024-09"
LAST_MONTH = "2026-08"
DATA_START = date(2024, 9, 1)
DATA_END = date(2026, 8, 31)
LOCAL_TZ = "Asia/Kuala_Lumpur"
UTC_OFFSET_HOURS = 8  # Malaysia has no daylight saving

# The SQL layers, run in this order by the model stage
MODEL_LAYERS = ["01_staging", "02_marts", "03_kpi"]


def connect(read_only: bool = False):
    """Open the warehouse with the session pinned to UTC.

    Pinning the session time zone means a timestamp without an offset is
    read the same way on a laptop in Malaysia and on a CI runner in UTC.
    """
    import duckdb

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=read_only)
    con.execute("SET TimeZone = 'UTC'")
    con.execute("SET enable_progress_bar = false")
    return con
