-- Growth and onboarding KPIs by month, and acquisition economics by channel and cohort.
CREATE OR REPLACE TABLE kpi.growth_monthly AS
WITH months AS (SELECT DISTINCT month_start FROM marts.dim_date),
funnel AS (
    SELECT
        start_month                                                     AS month_start,
        count(*)                                                        AS applications_started,
        avg(CASE WHEN is_opened THEN 1.0 ELSE 0.0 END)                  AS onboarding_conversion,
        avg(CASE WHEN liveness_passed_ts IS NOT NULL THEN 1.0 ELSE 0.0 END)
            FILTER (WHERE id_scanned_ts IS NOT NULL)                    AS ekyc_completion_rate
    FROM marts.fct_onboarding_funnel
    GROUP BY 1
),
opened AS (
    SELECT cohort_month AS month_start, count(*) AS new_customers
    FROM marts.dim_customer
    GROUP BY 1
),
spend AS (
    SELECT
        month_start,
        sum(spend) FILTER (WHERE is_acquisition)                        AS acquisition_spend,
        bool_or(is_missing AND is_acquisition)                          AS spend_incomplete
    FROM marts.fct_marketing_spend
    GROUP BY 1
),
m3 AS (   -- customers who opened three months before the reporting month, and were active in it
    SELECT
        c.cohort_month + INTERVAL 3 MONTH                               AS month_start,
        avg(CASE WHEN a.is_active THEN 1.0 ELSE 0.0 END)                AS m3_active_rate
    FROM marts.dim_customer AS c
    LEFT JOIN marts.fct_customer_monthly AS a
           ON a.customer_id = c.customer_id AND a.months_since_open = 3
    WHERE c.cohort_month + INTERVAL 3 MONTH <= DATE '2026-08-01'
    GROUP BY 1
)
SELECT
    m.month_start,
    f.applications_started,
    o.new_customers,
    f.onboarding_conversion,
    f.ekyc_completion_rate,
    CASE WHEN s.spend_incomplete THEN NULL ELSE s.acquisition_spend END AS acquisition_spend,
    CASE WHEN s.spend_incomplete THEN NULL ELSE s.acquisition_spend / o.new_customers END AS cac,
    coalesce(s.spend_incomplete, false)                                 AS spend_incomplete,
    m3.m3_active_rate
FROM months AS m
LEFT JOIN funnel AS f ON f.month_start = m.month_start
LEFT JOIN opened AS o ON o.month_start = m.month_start
LEFT JOIN spend AS s ON s.month_start = m.month_start
LEFT JOIN m3 ON CAST(m3.month_start AS DATE) = m.month_start;

-- Channel economics by cohort month: what a sign-up costs, and what a customer who is still
-- active three months later costs.
CREATE OR REPLACE TABLE kpi.channel_monthly AS
WITH starts AS (
    SELECT start_month AS month_start, acquisition_channel AS channel, count(*) AS applications_started
    FROM marts.fct_onboarding_funnel GROUP BY 1, 2
),
cohort AS (
    SELECT
        c.cohort_month                                                  AS month_start,
        c.acquisition_channel                                           AS channel,
        count(*)                                                        AS new_customers,
        count(*) FILTER (WHERE a.is_active)                             AS m3_active_customers,
        c.cohort_month + INTERVAL 3 MONTH <= DATE '2026-08-01'          AS m3_observed
    FROM marts.dim_customer AS c
    LEFT JOIN marts.fct_customer_monthly AS a
           ON a.customer_id = c.customer_id AND a.months_since_open = 3
    GROUP BY 1, 2, 5
),
spend AS (
    SELECT month_start, channel, sum(spend) AS spend, bool_or(is_missing) AS spend_missing
    FROM marts.fct_marketing_spend
    WHERE is_acquisition
    GROUP BY 1, 2
)
SELECT
    c.month_start,
    c.channel,
    ch.channel_name,
    ch.is_paid,
    st.applications_started,
    c.new_customers,
    CASE WHEN s.spend_missing THEN NULL ELSE s.spend END                AS spend,
    CASE WHEN s.spend_missing OR NOT ch.is_paid THEN NULL ELSE s.spend / c.new_customers END AS cost_per_new_customer,
    CASE WHEN c.m3_observed THEN c.m3_active_customers END              AS m3_active_customers,
    CASE WHEN c.m3_observed THEN c.m3_active_customers * 1.0 / c.new_customers END AS m3_active_rate,
    CASE WHEN c.m3_observed AND ch.is_paid AND NOT s.spend_missing AND c.m3_active_customers > 0
         THEN s.spend / c.m3_active_customers END                       AS cost_per_m3_active_customer
FROM cohort AS c
JOIN marts.dim_channel AS ch ON ch.channel = c.channel
LEFT JOIN starts AS st ON st.month_start = c.month_start AND st.channel = c.channel
LEFT JOIN spend AS s ON s.month_start = c.month_start AND s.channel = c.channel;
