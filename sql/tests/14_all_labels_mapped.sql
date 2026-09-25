-- name: all_labels_mapped
-- severity: error
-- description: Every raw label (channel, state, employment, product, transaction code, card status, entry mode, merchant, marketing line) maps to a standard value.
-- break: UPDATE staging.stg_app_events SET channel = NULL WHERE event_id = 'ev_00000001'
SELECT 'app channel' AS label_type, channel_raw AS raw_label, count(*) AS rows_affected FROM staging.stg_app_events WHERE channel IS NULL GROUP BY 2
UNION ALL SELECT 'state', state_raw, count(*) FROM staging.stg_customers WHERE state IS NULL GROUP BY 2
UNION ALL SELECT 'employment', employment_type_raw, count(*) FROM staging.stg_customers WHERE employment_type IS NULL GROUP BY 2
UNION ALL SELECT 'product code', product_code_raw, count(*) FROM staging.stg_accounts WHERE product_code IS NULL GROUP BY 2
UNION ALL SELECT 'ledger transaction code', txn_code_raw, count(*) FROM staging.stg_ledger_postings WHERE txn_type IS NULL GROUP BY 2
UNION ALL SELECT 'card status', status_raw, count(*) FROM staging.stg_card_authorisations WHERE status IS NULL GROUP BY 2
UNION ALL SELECT 'card entry mode', entry_mode_raw, count(*) FROM staging.stg_card_authorisations WHERE entry_mode IS NULL GROUP BY 2
UNION ALL SELECT 'merchant code', CAST(mcc AS VARCHAR), count(*) FROM staging.stg_card_authorisations WHERE merchant_category IS NULL GROUP BY 2
UNION ALL SELECT 'marketing sheet line', line_label, count(*) FROM staging.stg_marketing_spend WHERE row_type IS NULL GROUP BY 2
UNION ALL SELECT 'marketing month header', month_label, count(*) FROM staging.stg_marketing_spend WHERE month_start IS NULL GROUP BY 2
