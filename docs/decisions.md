# Decision log

Each design choice in this project and the reason for it, newest first. Add an entry every working session.

## 2026-09-26: Check the Excel pack by recalculating it in LibreOffice

- **Decision:** After building the pack, open a copy in LibreOffice (headless), recalculate every formula, and compare the results with the warehouse: no error values, no pasted numbers on report sheets, every monthly value, the scorecard and the trend, and every row of the pack's own Checks sheet.
- **Why:** openpyxl writes formulas without their results, so the file alone proves nothing about the numbers. The definition of done asks for zero formula errors and totals that match SQL; this makes both a test that runs on every build.
- **Alternatives:** Opening it in Excel by hand each month is slow and easy to skip. Writing values instead of formulas would pass trivially, but the pack would no longer recalculate when a reader picks a month.

## 2026-09-26: Build the Excel pack from live formulas, named ranges and Excel 2007 functions

- **Decision:** Only the data sheets hold typed-in numbers. The Scorecard, Trend and Monthly KPIs sheets are formulas (`SUMIFS`, `COUNTIFS`, `INDEX`/`MATCH`, `EDATE`) over named ranges such as `data_value` and `report_month`, and the reader changes two yellow cells.
- **Why:** The plan asks for live formulas, not pasted values. Named ranges make the formulas readable; functions from Excel 2007 work in every version of Excel, in LibreOffice and in Google Sheets.
- **Alternatives:** `XLOOKUP` and dynamic arrays are neater, but fail in older Excel and in LibreOffice. A pivot table cannot be built reliably from Python.

## 2026-09-26: Store interest accruals and average balances as exact decimals

- **Decision:** `interest_accrued`, `interest_income_accrued`, `average_balance` and `hours_to_open` are cast to `DECIMAL` in the marts.
- **Why:** They were rounded but stored as floating point, and DuckDB sums floats in parallel in whatever order its threads finish, so the last digits of net interest income could differ between two runs. Exact decimals sum the same way every time.
- **Alternatives:** Running DuckDB on one thread makes float sums repeatable but slows every query; rounding the outputs hides the problem instead of removing it.

## 2026-09-26: Give the dashboard tidy CSV extracts, one per need

- **Decision:** The publish stage writes 15 small CSVs to `dashboards/extracts/`, mostly long (tidy) tables, and they are committed to the repo.
- **Why:** Tableau Public cannot connect to a database, and CSVs work in Tableau, Power BI and Qlik alike. Aggregating in SQL keeps the logic in the warehouse, so the dashboard and the Excel pack cannot disagree.
- **Alternatives:** Connecting Tableau to row-level facts would put business logic in Tableau calculated fields, out of reach of the checks.

## 2026-09-26: Never show status by colour alone; use a colour-blind-safe palette and no dual axes

- **Decision:** Every status carries an icon and a word (▲ On plan, ● Watch, ▼ Off plan) as well as a colour. Series colours come from a palette validated for colour-blind readers, in a fixed order. Two measures of different scale get two charts, never a dual axis.
- **Why:** About one man in twelve has some colour vision deficiency, and reports get printed in black and white. Dual axes let the chart-maker make any two lines look related.
- **Alternatives:** Traffic-light colours alone are common in banks, and are unreadable for many people.

## 2026-09-26: Segment customers with k-means on four behaviour features, k chosen by silhouette

- **Decision:** Customers with no transactions of their own for six months are "Dormant" by rule. The rest are clustered on four standardised features (average balance and card purchases, both logged; card share of spending; share of months active), with k from 2 to 8 chosen by silhouette score, and each cluster named from its profile rather than its number.
- **Why:** Dormant customers have no behaviour to cluster and would form a tight, meaningless cluster that inflates the silhouette score. Logging the skewed features stops a few rich customers from dominating. Names from profiles survive a rerun that renumbers the clusters.
- **Alternatives:** RFM scoring is simpler but fixed in advance; Gaussian mixtures handle overlapping groups but are harder to explain to a business audience.

## 2026-09-26: Pool vintage curves by credit policy, and plot each only while half its loans are observed

- **Decision:** Vintage curves are pooled across the monthly vintages approved under each policy (v1, v2, v3), and each curve stops at the month on book that at least half of that policy's loans have reached.
- **Why:** The question is whether the policy change mattered, so the policy is the unit. Pooled curves dip at the right-hand end when only the earliest vintages have reached that age; the coverage rule stops the tail from misleading.
- **Alternatives:** One curve per monthly vintage is noisier; comparing PAR30 alone mixes old and new loans.

## 2026-09-26: Run the eKYC A/B test as a Bayesian test with its rules written down first

- **Decision:** The primary metric, the fraud guardrail, the decision rule and a sample-ratio check are stored in `reference.experiments` before the results are read. The readout checks the sample ratio first, then uses Beta(1, 1) priors and 200,000 posterior draws.
- **Why:** A Bayesian readout answers the question the business asks ("how likely is the new flow better, and by how much?"). Writing the rules first stops the analyst from choosing the metric that looks best afterwards.
- **Alternatives:** A frequentist z-test gives a p-value, which is often misread as the probability the new flow is better.

## 2026-09-25: Judge acquisition channels on the cost of a customer still active in month 3

- **Decision:** Alongside cost per new customer (CAC), report cost per customer still active in their third month, by channel and cohort.
- **Why:** A cheap sign-up who never uses the account is not cheap. Month 3 is late enough to see who stays and early enough to act on.
- **Alternatives:** Lifetime value needs revenue and years of history the bank does not have yet.

## 2026-09-25: Report cohort measures only once their window has closed

- **Decision:** Card activation within 30 days, month-3 activity, fixed deposit retention after 30 days and month-6 delinquency stay blank for cohorts whose window is still open.
- **Why:** Otherwise the latest month always looks worse: in August 2026, card activation would show 50% only because late-August customers had not had 30 days yet.
- **Alternatives:** Showing the partial figure with a footnote invites exactly the wrong conclusion.

## 2026-09-25: Prove each check works by breaking the data inside a transaction

- **Decision:** For each error and warning check, run it on clean data, break the data on purpose in a transaction, run it again, roll back, and run it a third time. A check that does not fire is a failure.
- **Why:** A check that never fails might be testing nothing. Rolling back leaves the warehouse exactly as it was.
- **Alternatives:** Hand-made broken test files drift out of date as the model changes.

## 2026-09-25: Write checks as SQL that returns the failing rows, graded error, warn or info

- **Decision:** Each check in `sql/tests/` is a query returning the rows that break a rule, with a header naming its severity. Errors stop the pipeline before anything is published; warnings are reported; info records numbers worth knowing.
- **Why:** A failure shows exactly which records are wrong. Not every problem should block a month-end report: a missing invoice needs a warning, not a stopped bank.
- **Alternatives:** Pass/fail assertions say that something is wrong but not what.

## 2026-09-25: Reconcile the ledger to balances, and the card processor to the ledger, to the sen

- **Decision:** Two reconciliations: every deposit account's month-end balance equals last month's plus the month's postings; every settled card authorisation posts to the ledger once, for the same amount, on its settlement date.
- **Why:** These are the tie-outs Finance runs; if they pass, the dashboard's money figures agree with the bank's books. The first also proves the time-zone handling, since a UTC month-end would put about 53,000 account-months out of balance.
- **Alternatives:** Comparing monthly totals only can hide offsetting errors between accounts.

## 2026-09-25: Status that respects each KPI's direction, with an amber band from the catalog

- **Decision:** Green at or better than plan, amber when worse by less than the KPI's amber band (a share of plan), red beyond it; "better" means higher for deposits and lower for cost of funds and PAR30.
- **Why:** A single rule for every KPI would turn a falling PAR30 red. Putting the band in the catalog lets each owner set their own tolerance.
- **Alternatives:** A fixed ±5% for every KPI is simpler, but too loose for PAR30 and too tight for new customers.

## 2026-09-25: Define every KPI once in a catalog, and stack all KPIs in one long table

- **Decision:** `kpi_catalog.csv` holds each KPI's definition, formula, owner, unit, direction, amber band, target and SQL source; `kpi.kpi_monthly` holds every KPI's value by month in long format.
- **Why:** The scorecard, the dashboard, the Excel pack and the KPI dictionary all read the same definition and the same numbers. A check fails if any catalog KPI has no values.
- **Alternatives:** Defining KPIs in each tool is how banks end up with three versions of "active customer".

## 2026-09-25: A star schema with all three kinds of fact table

- **Decision:** Transaction facts for postings and card authorisations, periodic snapshots for balances, loans and customer activity, and an accumulating snapshot for the onboarding funnel.
- **Why:** Each kind fits its question: money flows sum; balances and arrears are states at month end; the funnel is a process with fixed steps.
- **Alternatives:** One wide table per report is quicker to start but repeats logic and cannot answer new questions.

## 2026-09-25: Convert to Malaysia time in staging, with the session pinned to UTC

- **Decision:** Every timestamp is parsed as an instant (sources send UTC, `+08:00` or no offset at all), and dates and months are taken in Asia/Kuala_Lumpur. The DuckDB session time zone is fixed to UTC.
- **Why:** The bank's month ends at midnight in Malaysia, not in London. Pinning the session means a timestamp without an offset is read the same way on any machine.
- **Alternatives:** Leaving times in UTC would count every posting made between midnight and 8 am Malaysia time on the 1st in the previous month.

## 2026-09-25: Keep money in exact units: integer sen in the simulator, decimals in the warehouse

- **Decision:** The simulator tracks balances in integer sen, and the warehouse casts money to `DECIMAL(18,2)`.
- **Why:** Floating point cannot represent most amounts in ringgit and sen exactly, so sums drift and reconciliations would fail by fractions of a sen.
- **Alternatives:** Floats with rounding at the end make reconciliations fuzzy, and a fuzzy tie-out proves little.

## 2026-09-25: Load every source into the warehouse as text first

- **Decision:** The load stage copies each file into `raw` with every column as text, and logs row counts; all typing and cleaning happens in SQL in `staging`.
- **Why:** A bad value can never stop the load, every cleaning rule is visible and testable in one place, and staging can be rebuilt without rereading the files.
- **Alternatives:** Letting the loader guess types is quicker, but a guess that changes with the data (a date column that is sometimes blank) breaks the pipeline in ways that are hard to see.

## 2026-09-25: Use DuckDB as the warehouse

- **Decision:** A single DuckDB file holds all six schemas, and every transformation is SQL.
- **Why:** It is free, runs in-process with no server, reads CSV, JSON, Parquet and Excel-derived data directly, and is fast on millions of rows. The SQL carries over to a bank's warehouse.
- **Alternatives:** PostgreSQL needs a server and is slower for analytical queries; SQLite lacks the analytical SQL (`QUALIFY`, `UNPIVOT`, time zones) used here.

## 2026-09-25: Simulate the bank, with planted stories and real-world mess

- **Decision:** Generate 24 months of six source systems from a fixed seed (option A in the plan), with five stories planted on purpose and the kinds of mess real extracts have.
- **Why:** Real bank data is not available, the public alternatives are old or not Malaysian, and planted stories with known answers prove the methods can find them.
- **Alternatives:** The Berka Czech bank dataset (real but from the 1990s, with no app, funnel or marketing data); Malaysian public data from data.gov.my and BNM (real, but aggregates only).

## 2026-09-25: Pin exact package versions, including NumPy

- **Decision:** Pin every package in `requirements.txt` to an exact version, and list NumPy even though pandas already installs it.
- **Why:** The simulator is seeded, so the same seed has to give the same data on every machine and in CI. NumPy does not promise the same random numbers across versions, so an unpinned NumPy could quietly change the data and every number built on it.
- **Alternatives:** Version ranges (`>=`) are easier to upgrade but let results drift. A lock file of every sub-dependency is the most reproducible, but noisy for a project this size.

## 2026-09-25: Keep raw data and the warehouse out of Git; commit a sample of each source

- **Decision:** `data/raw/` and the DuckDB warehouse file are ignored. A small sample of each source goes in `data/sample/`.
- **Why:** The pipeline rebuilds both from a fixed seed, so committing them adds size without adding information. The samples let visitors see each source's format without running anything.
- **Alternatives:** Committing all the data makes the repo large and changes every file on each regeneration. Committing none leaves visitors unable to see the formats.
