-- Engagement KPIs by month.
CREATE OR REPLACE TABLE kpi.engagement_monthly AS
SELECT
    m.month_start,
    count(*) FILTER (WHERE c.closed_date IS NULL OR c.closed_date > last_day(m.month_start)) AS open_customers,
    count(*) FILTER (WHERE m.is_active)                                 AS monthly_active_customers,
    count(*) FILTER (WHERE m.is_active) * 1.0
        / count(*) FILTER (WHERE c.closed_date IS NULL OR c.closed_date > last_day(m.month_start)) AS active_customer_rate,
    sum(m.customer_txns) * 1.0 / nullif(count(*) FILTER (WHERE m.is_active), 0) AS txns_per_active_customer
FROM marts.fct_customer_monthly AS m
JOIN marts.dim_customer AS c ON c.customer_id = m.customer_id
GROUP BY 1;
