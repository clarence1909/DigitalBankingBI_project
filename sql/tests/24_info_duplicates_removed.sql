-- name: duplicates_removed_in_staging
-- severity: info
-- description: How many duplicate or superseded source rows staging removed (app retries, re-extracted customers, card status updates and resends).
SELECT 'app events' AS source, (SELECT count(*) FROM raw.app_events) AS raw_rows,
       (SELECT count(*) FROM staging.stg_app_events) AS staged_rows
UNION ALL SELECT 'customers', (SELECT count(*) FROM raw.customers), (SELECT count(*) FROM staging.stg_customers)
UNION ALL SELECT 'card authorisations', (SELECT count(*) FROM raw.card_authorisations),
       (SELECT count(*) FROM staging.stg_card_authorisations)
