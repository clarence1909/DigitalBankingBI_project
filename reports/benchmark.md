# Query benchmark

Written by `python -m src.benchmark`. Each time is the median of five runs on the warehouse built by `python run_pipeline.py`. All data is synthetic.

**Machine:** Linux x86_64, 2 CPU cores, DuckDB 1.5.5 using 2 threads.

## The heaviest queries

| Query | Main table | Rows | Median time |
|---|---|---:|---:|
| Deposits by month (the KPI query) | `marts.fct_account_balances_monthly` | 362,720 | 7 ms |
| Reconciliation 1, account by account | `marts.fct_ledger_postings` | 2,965,311 | 245 ms |
| Card spend by merchant category | `marts.fct_card_authorisations` | 1,157,070 | 10 ms |
| Monthly active customers | `marts.fct_customer_monthly` | 334,469 | 3 ms |
| Scorecard for one month (what the dashboard reads) | `kpi.scorecard` | 140 | 1 ms |

## Ten times the data

The ledger postings copied 10 times over (each copy on its own accounts), then summarised by month and transaction type with a distinct count of accounts, the most expensive kind of query here.

| Data | Rows | Median time |
|---|---:|---:|
| As built | 2,965,311 | 408 ms |
| 10 times | 29,653,110 | 4,975 ms |

Ten times the rows took 12.2 times as long, so the work grows roughly in line with the data. The [solution design](../docs/03_solution_design.md) says what a real bank would change at larger scale.
