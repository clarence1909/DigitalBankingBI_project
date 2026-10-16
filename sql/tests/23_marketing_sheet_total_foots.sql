-- name: marketing_sheet_total_foots
-- severity: warn
-- description: The TOTAL row typed into the marketing sheet equals the sum of its spend lines. Reporting uses the lines, never the TOTAL row.
-- break: UPDATE staging.stg_marketing_spend SET spend = spend + 1 WHERE row_type = 'spend' AND channel = 'tiktok' AND month_start = DATE '2025-03-01'
WITH lines AS (
    SELECT month_start, sum(coalesce(spend, 0)) AS sum_of_lines
    FROM staging.stg_marketing_spend
    WHERE row_type = 'spend'
    GROUP BY 1
),
total AS (
    SELECT month_start, spend AS sheet_total
    FROM staging.stg_marketing_spend
    WHERE row_type = 'total'
)
SELECT t.month_start, t.sheet_total, l.sum_of_lines, t.sheet_total - l.sum_of_lines AS difference
FROM total AS t
JOIN lines AS l ON l.month_start = t.month_start
WHERE t.sheet_total <> l.sum_of_lines
