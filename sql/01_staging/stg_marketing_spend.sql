-- The marketing team's hand-kept spend sheet, reshaped from wide (a column per month) to long.
-- Cleaning rules:
--   * UNPIVOT the month columns; INCLUDE NULLS keeps months left blank (no spend).
--   * Month headers are text ('Sep-24') except where Excel turned them into dates.
--   * Values can be numbers, text with separators ('8,018.16'), text with 'RM', '-' (none)
--     or 'n/a' (invoice not received yet, kept as missing, not zero).
--   * The TOTAL row and the footnote are kept, labelled by row_type, so the sheet's own
--     total can be checked; reporting only uses row_type = 'spend'.
CREATE OR REPLACE TABLE staging.stg_marketing_spend AS
WITH long AS (
    FROM (SELECT * EXCLUDE ("Total", "Notes") FROM raw.marketing_spend)
    UNPIVOT INCLUDE NULLS (spend_text FOR month_label IN (COLUMNS(* EXCLUDE (sheet_row, "Channel"))))
),
parsed AS (
    SELECT
        CAST(sheet_row AS INTEGER)                                  AS sheet_row,
        trim("Channel")                                             AS line_label,
        month_label,
        coalesce(CAST(try_strptime(month_label, '%b-%y') AS DATE),
                 CAST(TRY_CAST(month_label AS TIMESTAMP) AS DATE))  AS month_start,
        spend_text,
        CASE
            WHEN spend_text IS NULL OR trim(spend_text) IN ('', '-') THEN 0
            WHEN lower(trim(spend_text)) = 'n/a' THEN NULL
            ELSE TRY_CAST(regexp_replace(spend_text, '[^0-9.\-]', '', 'g') AS DECIMAL(18, 2))
        END                                                         AS spend,
        coalesce(lower(trim(spend_text)) = 'n/a', false)            AS is_missing
    FROM long
)
SELECT
    p.sheet_row,
    p.line_label,
    lm.row_type,
    nullif(lm.channel, '')                                          AS channel,
    lm.is_acquisition,
    p.month_label,
    p.month_start,
    p.spend_text,
    p.spend,
    p.is_missing
FROM parsed AS p
LEFT JOIN reference.marketing_line_map AS lm
    ON lm.raw_label = lower(p.line_label);
