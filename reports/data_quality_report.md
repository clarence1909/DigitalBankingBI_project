# Data quality report

Written by `python run_pipeline.py` (check stage). All data is synthetic.

**26 checks: 22 passed, 2 warnings, 2 for information, 0 failed.** Errors block the pipeline; warnings and information do not.

| Check | Severity | Result | Rows | What it tests |
|---|---|---|---:|---|
| `unique_customer_id` | error | PASS | 0 | Each customer appears once in dim_customer. |
| `unique_account_id` | error | PASS | 0 | Each account appears once in dim_account. |
| `unique_posting_id` | error | PASS | 0 | Each ledger posting appears once. |
| `unique_auth_id` | error | PASS | 0 | Each card authorisation appears once after status updates and resends are resolved. |
| `unique_applicant_id` | error | PASS | 0 | The onboarding funnel has one row per applicant. |
| `unique_balance_account_month` | error | PASS | 0 | Month-end balances have one row per account per month. |
| `unique_loan_month` | error | PASS | 0 | The loan status snapshot has one row per loan per month. |
| `no_orphan_accounts` | error | PASS | 0 | Every account belongs to a known customer. |
| `no_orphan_postings` | error | PASS | 0 | Every ledger posting is on a known account. |
| `no_orphan_card_authorisations` | error | PASS | 0 | Every card authorisation is on a card issued by Kelip Bank. |
| `no_orphan_loans` | error | PASS | 0 | Every loan belongs to a known customer. |
| `customers_have_applications` | error | PASS | 0 | Every customer can be traced back to their sign-up in the app. |
| `funnel_steps_in_order` | error | PASS | 0 | Applicants pass the onboarding steps in order: each step needs the one before it, never earlier in time. |
| `all_labels_mapped` | error | PASS | 0 | Every raw label (channel, state, employment, product, transaction code, card status, entry mode, merchant, marketing line) maps to a standard value. |
| `no_negative_balances` | warn | PASS | 0 | Deposit accounts never close a month overdrawn (Kelip Bank offers no overdrafts). |
| `fd_empty_after_maturity` | error | PASS | 0 | A matured fixed deposit has a zero balance from its maturity month on. |
| `ratio_kpis_between_0_and_1` | error | PASS | 0 | Every KPI measured as a share lies between 0% and 100%. |
| `dpd_matches_arrears` | error | PASS | 0 | An active loan is past due exactly when it has instalments in arrears. |
| `recon_ledger_to_balances` | error | PASS | 0 | Reconciliation 1: for every account and month, last month's balance plus the month's postings (Malaysia time) equals the balance core banking reports, to the sen. |
| `recon_card_processor_to_ledger` | error | PASS | 0 | Reconciliation 2: every settled card authorisation posts to the ledger once, for the same amount, on its settlement date; and nothing posts without a settled authorisation. |
| `kpi_catalog_coverage` | error | PASS | 0 | Every KPI in the catalog has values, and every scorecard KPI has a plan for the latest month. |
| `marketing_invoices_missing` | warn | WARN | 1 | Marketing spend lines typed as n/a (invoice not received). Cost per customer is left blank for those months rather than understated. |
| `marketing_sheet_total_foots` | warn | WARN | 1 | The TOTAL row typed into the marketing sheet equals the sum of its spend lines. Reporting uses the lines, never the TOTAL row. |
| `duplicates_removed_in_staging` | info | INFO | 3 | How many duplicate or superseded source rows staging removed (app retries, re-extracted customers, card status updates and resends). |
| `late_card_settlements` | info | INFO | 24 | Card purchases that settled more than three days after authorisation, and those that settled in a later month, by authorisation month. These explain timing differences when card spend is compared by authorisation month instead of settlement month. |
| `schema_yml_matches_warehouse` | error | PASS | 0 | sql/schema.yml describes exactly the tables and columns in the marts and kpi schemas. |

## Warnings and information

### `marketing_invoices_missing` (WARN, 1 rows)

Marketing spend lines typed as n/a (invoice not received). Cost per customer is left blank for those months rather than understated.

| line_label | month_start | spend_text |
|---|---|---|
| Facebook / Instagram | 2026-08-01 | n/a |


### `marketing_sheet_total_foots` (WARN, 1 rows)

The TOTAL row typed into the marketing sheet equals the sum of its spend lines. Reporting uses the lines, never the TOTAL row.

| month_start | sheet_total | sum_of_lines | difference |
|---|---|---|---|
| 2026-01-01 | 41,608.90 | 41,108.90 | 500.00 |


### `duplicates_removed_in_staging` (INFO, 3 rows)

How many duplicate or superseded source rows staging removed (app retries, re-extracted customers, card status updates and resends).

| source | raw_rows | staged_rows |
|---|---|---|
| app events | 329161 | 324268 |
| customers | 32669 | 32574 |
| card authorisations | 1191315 | 1157070 |


### `late_card_settlements` (INFO, 24 rows)

Card purchases that settled more than three days after authorisation, and those that settled in a later month, by authorisation month. These explain timing differences when card spend is compared by authorisation month instead of settlement month.

| auth_month | late_settlements | settled_next_month | amount_settled_next_month |
|---|---|---|---|
| 2024-09-01 | 41 | 340 | 47,909.67 |
| 2024-10-01 | 101 | 521 | 76,493.97 |
| 2024-11-01 | 160 | 728 | 106,123.88 |
| 2024-12-01 | 224 | 825 | 127,010.76 |
| 2025-01-01 | 268 | 764 | 128,575.31 |


## Reconciliation 1: ledger postings to month-end balances

Opening balance plus the month's postings (by Malaysia-time posting date) against the closing balances core banking reports, summed over all savings and fixed deposit accounts. The check above does the same test account by account.

| month_start | opening_balance | net_postings | closing_balance | difference |
|---|---|---|---|---|
| 2024-09-01 | 0.00 | 2,433,161.92 | 2,433,161.92 | 0.00 |
| 2024-10-01 | 2,433,161.92 | 2,864,305.63 | 5,297,467.55 | 0.00 |
| 2024-11-01 | 5,297,467.55 | 2,809,529.39 | 8,106,996.94 | 0.00 |
| 2024-12-01 | 8,106,996.94 | 3,499,858.67 | 11,606,855.61 | 0.00 |
| 2025-01-01 | 11,606,855.61 | 4,146,045.23 | 15,752,900.84 | 0.00 |
| 2025-02-01 | 15,752,900.84 | 4,484,496.71 | 20,237,397.55 | 0.00 |
| 2025-03-01 | 20,237,397.55 | 5,162,918.41 | 25,400,315.96 | 0.00 |
| 2025-04-01 | 25,400,315.96 | 6,495,971.29 | 31,896,287.25 | 0.00 |
| 2025-05-01 | 31,896,287.25 | 6,602,036.13 | 38,498,323.38 | 0.00 |
| 2025-06-01 | 38,498,323.38 | 5,055,987.92 | 43,554,311.30 | 0.00 |
| 2025-07-01 | 43,554,311.30 | 6,365,431.49 | 49,919,742.79 | 0.00 |
| 2025-08-01 | 49,919,742.79 | 5,363,409.48 | 55,283,152.27 | 0.00 |
| 2025-09-01 | 55,283,152.27 | 5,181,872.53 | 60,465,024.80 | 0.00 |
| 2025-10-01 | 60,465,024.80 | 4,467,563.41 | 64,932,588.21 | 0.00 |
| 2025-11-01 | 64,932,588.21 | 5,270,576.83 | 70,203,165.04 | 0.00 |
| 2025-12-01 | 70,203,165.04 | 6,244,139.12 | 76,447,304.16 | 0.00 |
| 2026-01-01 | 76,447,304.16 | 6,064,995.44 | 82,512,299.60 | 0.00 |
| 2026-02-01 | 82,512,299.60 | 7,224,098.47 | 89,736,398.07 | 0.00 |
| 2026-03-01 | 89,736,398.07 | 5,684,889.17 | 95,421,287.24 | 0.00 |
| 2026-04-01 | 95,421,287.24 | 6,990,306.82 | 102,411,594.06 | 0.00 |
| 2026-05-01 | 102,411,594.06 | 7,457,404.48 | 109,868,998.54 | 0.00 |
| 2026-06-01 | 109,868,998.54 | 7,099,595.36 | 116,968,593.90 | 0.00 |
| 2026-07-01 | 116,968,593.90 | 7,944,064.85 | 124,912,658.75 | 0.00 |
| 2026-08-01 | 124,912,658.75 | 7,269,991.81 | 132,182,650.56 | 0.00 |


## Reconciliation 2: card processor to ledger

Settled authorisations by settlement month against card purchases posted to the ledger. Compared by authorisation month instead, late settlements create timing differences, shown in the last column; that is why the tie-out uses settlement dates.

| month_start | processor_settled | ledger_card_postings | difference | approved_by_auth_month | timing_difference_if_compared_by_auth_month |
|---|---|---|---|---|---|
| 2024-09-01 | 319,970.43 | 319,970.43 | 0.00 | 367,880.10 | 47,909.67 |
| 2024-10-01 | 759,451.54 | 759,451.54 | 0.00 | 788,035.84 | 28,584.30 |
| 2024-11-01 | 1,283,662.45 | 1,283,662.45 | 0.00 | 1,313,292.36 | 29,629.91 |
| 2024-12-01 | 1,791,308.22 | 1,791,308.22 | 0.00 | 1,812,195.10 | 20,886.88 |
| 2025-01-01 | 2,828,194.61 | 2,828,194.61 | 0.00 | 2,829,759.16 | 1,564.55 |
| 2025-02-01 | 3,446,472.16 | 3,446,472.16 | 0.00 | 3,557,116.34 | 110,644.18 |
| 2025-03-01 | 4,070,805.42 | 4,070,805.42 | 0.00 | 4,040,525.34 | -30,280.08 |
| 2025-04-01 | 4,518,433.10 | 4,518,433.10 | 0.00 | 4,553,091.54 | 34,658.44 |
| 2025-05-01 | 4,980,276.14 | 4,980,276.14 | 0.00 | 4,993,657.22 | 13,381.08 |
| 2025-06-01 | 5,833,708.46 | 5,833,708.46 | 0.00 | 5,870,390.13 | 36,681.67 |
| 2025-07-01 | 7,044,832.33 | 7,044,832.33 | 0.00 | 7,079,084.50 | 34,252.17 |
| 2025-08-01 | 7,896,663.58 | 7,896,663.58 | 0.00 | 7,896,476.96 | -186.62 |
| 2025-09-01 | 8,363,593.40 | 8,363,593.40 | 0.00 | 8,423,964.92 | 60,371.52 |
| 2025-10-01 | 9,258,956.85 | 9,258,956.85 | 0.00 | 9,253,548.04 | -5,408.81 |
| 2025-11-01 | 10,085,542.41 | 10,085,542.41 | 0.00 | 10,171,547.63 | 86,005.22 |
| 2025-12-01 | 10,605,785.65 | 10,605,785.65 | 0.00 | 10,645,261.28 | 39,475.63 |
| 2026-01-01 | 10,850,337.55 | 10,850,337.55 | 0.00 | 10,805,732.81 | -44,604.74 |
| 2026-02-01 | 11,546,068.50 | 11,546,068.50 | 0.00 | 11,618,471.19 | 72,402.69 |
| 2026-03-01 | 12,377,731.85 | 12,377,731.85 | 0.00 | 12,345,909.72 | -31,822.13 |
| 2026-04-01 | 13,315,520.80 | 13,315,520.80 | 0.00 | 13,402,198.51 | 86,677.71 |
| 2026-05-01 | 14,247,942.11 | 14,247,942.11 | 0.00 | 14,305,938.80 | 57,996.69 |
| 2026-06-01 | 15,116,130.47 | 15,116,130.47 | 0.00 | 15,095,088.46 | -21,042.01 |
| 2026-07-01 | 15,628,972.27 | 15,628,972.27 | 0.00 | 15,686,699.91 | 57,727.64 |
| 2026-08-01 | 16,940,845.53 | 16,940,845.53 | 0.00 | 16,255,339.97 | -685,505.56 |


## Ad-hoc stakeholder queries

Each query in `sql/adhoc/` runs on every build; its answer is saved as a CSV.

- `sql/adhoc/01_cost_per_retained_customer_by_channel.sql`: Question (Head of Growth, Q05): For customers who opened from January to May 2026, what did each paid channel cost per new customer, and per customer still active three months later? ([result](adhoc/01_cost_per_retained_customer_by_channel.csv), 5 rows)
- `sql/adhoc/02_raya_promo_funding.sql`: Question (Treasurer, Q14): How much of the money placed in the Raya FD promotion came out of customers' own Kelip savings, and how much was new money brought in from other banks? New money = transfers into the customer's savings in the three hours before the placement. ([result](adhoc/02_raya_promo_funding.csv), 1 rows)
- `sql/adhoc/03_top_card_categories.sql`: Question (Head of Cards, Q16): What did customers spend on with the debit card from June to August 2026, and how big is a typical purchase in each category? ([result](adhoc/03_top_card_categories.csv), 12 rows)
- `sql/adhoc/04_vintages_above_appetite.sql`: Question (Head of Credit Risk, Q19): Which monthly vintages have had more than 5% of loans 30+ days past due by month 6 on book, and which credit policy approved them? ([result](adhoc/04_vintages_above_appetite.csv), 6 rows)
- `sql/adhoc/05_onboarding_time_by_flow.sql`: Question (Head of Onboarding, Q09): In 2026, how long did it take to open an account, and how often did an application go to manual review, for each eKYC flow? ([result](adhoc/05_onboarding_time_by_flow.csv), 2 rows)
