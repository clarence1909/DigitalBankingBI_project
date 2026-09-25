# Decision log

Each design choice in this project and the reason for it, newest first. Add an entry every working session.

## 2026-09-25: Pin exact package versions, including NumPy

- **Decision:** Pin every package in `requirements.txt` to an exact version, and list NumPy even though pandas already installs it.
- **Why:** The simulator is seeded, so the same seed has to give the same data on every machine and in CI. NumPy does not promise the same random numbers across versions, so an unpinned NumPy could quietly change the data and every number built on it.
- **Alternatives:** Version ranges (`>=`) are easier to upgrade but let results drift. A lock file of every sub-dependency is the most reproducible, but noisy for a project this size.

## 2026-09-25: Keep raw data and the warehouse out of Git; commit a sample of each source

- **Decision:** `data/raw/` and the DuckDB warehouse file are ignored. A small sample of each source goes in `data/sample/`.
- **Why:** The pipeline rebuilds both from a fixed seed, so committing them adds size without adding information. The samples let visitors see each source's format without running anything.
- **Alternatives:** Committing all the data makes the repo large and changes every file on each regeneration. Committing none leaves visitors unable to see the formats.
