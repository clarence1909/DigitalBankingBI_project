"""Stage 3 of the pipeline: build the staging, mart and KPI layers from the SQL files.

Each layer is a folder under sql/. Files run in name order, which is why the
mart and KPI files carry number prefixes; every file rebuilds its tables with
CREATE OR REPLACE, so the warehouse always rebuilds from scratch.
"""

import time

from src.config import MODEL_LAYERS, SQL_DIR, connect


def run_layer(con, layer):
    files = sorted((SQL_DIR / layer).glob("*.sql"))
    for f in files:
        started = time.perf_counter()
        try:
            con.execute(f.read_text(encoding="utf-8"))
        except Exception as exc:  # show which file failed, then stop the pipeline
            raise SystemExit(f"SQL failed in sql/{layer}/{f.name}:\n{exc}") from exc
        print(f"      {layer}/{f.name:<38} {time.perf_counter() - started:5.1f} s")
    return len(files)


def main(layers=None):
    con = connect()
    total = 0
    for layer in layers or MODEL_LAYERS:
        total += run_layer(con, layer)
    con.close()
    print(f"      {total} SQL files run")


if __name__ == "__main__":
    main()
