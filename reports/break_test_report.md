# Break-test report

Each check is run on the clean warehouse, again after breaking the data on purpose inside a transaction, and a third time after rolling the break back. Written by `python -m src.break_tests`.

| Check | Severity | How the data was broken | Rows before | After break | After restore | Result |
|---|---|---|---:|---:|---:|---|
| `unique_customer_id` | error | `INSERT INTO marts.dim_customer SELECT * FROM marts.dim_customer LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `unique_account_id` | error | `INSERT INTO marts.dim_account SELECT * FROM marts.dim_account LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `unique_posting_id` | error | `INSERT INTO marts.fct_ledger_postings SELECT * FROM marts.fct_ledger_postings LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `unique_auth_id` | error | `INSERT INTO marts.fct_card_authorisations SELECT * FROM marts.fct_card_authorisations LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `unique_applicant_id` | error | `INSERT INTO marts.fct_onboarding_funnel SELECT * FROM marts.fct_onboarding_funnel LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `unique_balance_account_month` | error | `INSERT INTO marts.fct_account_balances_monthly SELECT * FROM marts.fct_account_balances_monthly LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `unique_loan_month` | error | `INSERT INTO marts.fct_loan_status_monthly SELECT * FROM marts.fct_loan_status_monthly LIMIT 1` | 0 | 1 | 0 | caught and restored |
| `no_orphan_accounts` | error | `UPDATE marts.dim_account SET customer_id = 'C9999999' WHERE account_id = (SELECT min(account_id) FROM marts.dim_account)` | 0 | 1 | 0 | caught and restored |
| `no_orphan_postings` | error | `UPDATE marts.fct_ledger_postings SET account_id = 'SA99999999' WHERE posting_id = 'LP0000000001'` | 0 | 1 | 0 | caught and restored |
| `no_orphan_card_authorisations` | error | `UPDATE marts.fct_card_authorisations SET card_id = 'DC99999999' WHERE auth_id = 'AU0000000001'` | 0 | 1 | 0 | caught and restored |
| `no_orphan_loans` | error | `UPDATE marts.fct_loan_status_monthly SET customer_id = 'C9999999' WHERE loan_id = 'PF00000001'` | 0 | 1 | 0 | caught and restored |
| `customers_have_applications` | error | `DELETE FROM marts.fct_onboarding_funnel WHERE applicant_id = (SELECT min(applicant_id) FROM marts.dim_customer)` | 0 | 1 | 0 | caught and restored |
| `funnel_steps_in_order` | error | `UPDATE marts.fct_onboarding_funnel SET phone_verified_ts = signup_started_ts - INTERVAL 1 HOUR WHERE applicant_id = 'A0000001'` | 0 | 1 | 0 | caught and restored |
| `all_labels_mapped` | error | `UPDATE staging.stg_app_events SET channel = NULL WHERE event_id = 'ev_00000001'` | 0 | 1 | 0 | caught and restored |
| `no_negative_balances` | warn | `UPDATE marts.fct_account_balances_monthly SET balance = -1 WHERE account_id = 'SA00000001' AND month_end_date = DATE '2024-09-30'` | 0 | 1 | 0 | caught and restored |
| `fd_empty_after_maturity` | error | `UPDATE marts.fct_account_balances_monthly SET balance = 100 WHERE account_id = (SELECT min(account_id) FROM marts.dim_account WHERE product_family = 'FD' AND account_status = 'MATURED') AND month_start = (SELECT date_trunc('month', maturity_date) FROM marts.dim_account WHERE account_id = (SELECT min(account_id) FROM marts.dim_account WHERE product_family = 'FD' AND account_status = 'MATURED'))` | 0 | 1 | 0 | caught and restored |
| `ratio_kpis_between_0_and_1` | error | `UPDATE kpi.kpi_monthly SET value = 1.5 WHERE kpi_id = 'K14' AND month_start = DATE '2026-08-01'` | 0 | 1 | 0 | caught and restored |
| `dpd_matches_arrears` | error | `UPDATE marts.fct_loan_status_monthly SET days_past_due = 45 WHERE loan_id = 'PF00000001' AND months_on_book = 0` | 0 | 1 | 0 | caught and restored |
| `recon_ledger_to_balances` | error | `UPDATE marts.fct_ledger_postings SET amount = amount - 0.01 WHERE posting_id = 'LP0000000001'` | 0 | 1 | 0 | caught and restored |
| `recon_card_processor_to_ledger` | error | `UPDATE marts.fct_card_authorisations SET amount = amount + 0.01 WHERE auth_id = (SELECT min(auth_id) FROM marts.fct_card_authorisations WHERE status = 'APPROVED' AND settlement_date IS NOT NULL)` | 0 | 1 | 0 | caught and restored |
| `kpi_catalog_coverage` | error | `DELETE FROM kpi.kpi_monthly WHERE kpi_id = 'K22'` | 0 | 1 | 0 | caught and restored |
| `marketing_invoices_missing` | warn | `UPDATE staging.stg_marketing_spend SET spend = NULL, is_missing = true WHERE channel = 'google_search' AND month_start = DATE '2026-07-01'` | 1 | 2 | 1 | caught and restored |
| `marketing_sheet_total_foots` | warn | `UPDATE staging.stg_marketing_spend SET spend = spend + 1 WHERE row_type = 'spend' AND channel = 'tiktok' AND month_start = DATE '2025-03-01'` | 1 | 2 | 1 | caught and restored |
| `schema_yml_matches_warehouse` | error | `ALTER TABLE marts.dim_channel ADD COLUMN undocumented_column INTEGER` | 0 | 1 | 0 | caught and restored |
