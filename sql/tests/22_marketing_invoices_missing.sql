-- name: marketing_invoices_missing
-- severity: warn
-- description: Marketing spend lines typed as n/a (invoice not received). Cost per customer is left blank for those months rather than understated.
-- break: UPDATE staging.stg_marketing_spend SET spend = NULL, is_missing = true WHERE channel = 'google_search' AND month_start = DATE '2026-07-01'
SELECT line_label, month_start, spend_text
FROM staging.stg_marketing_spend
WHERE row_type = 'spend' AND is_missing
