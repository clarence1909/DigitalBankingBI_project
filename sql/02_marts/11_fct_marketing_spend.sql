-- Marketing spend by line and month (from the hand-kept sheet; spend rows only).
CREATE OR REPLACE TABLE marts.fct_marketing_spend AS
SELECT
    month_start,
    channel,
    line_label,
    is_acquisition,
    spend,
    is_missing
FROM staging.stg_marketing_spend
WHERE row_type = 'spend';
