-- Calendar: one row per day of the reporting window (Sep 2024 to Aug 2026).
CREATE OR REPLACE TABLE marts.dim_date AS
SELECT
    CAST(d AS DATE)                                     AS date_day,
    year(d)                                             AS year,
    month(d)                                            AS month,
    quarter(d)                                          AS quarter,
    strftime(d, '%Y-%m')                                AS year_month,
    CAST(date_trunc('month', d) AS DATE)                AS month_start,
    last_day(CAST(d AS DATE))                           AS month_end,
    'FY' || year(d)                                     AS fiscal_year,
    dayofweek(d)                                        AS day_of_week,
    strftime(d, '%a')                                   AS day_name,
    CAST(d AS DATE) = last_day(CAST(d AS DATE))         AS is_month_end,
    dayofweek(d) IN (0, 6)                              AS is_weekend
FROM range(TIMESTAMP '2024-09-01', TIMESTAMP '2026-09-01', INTERVAL 1 DAY) AS t(d);
