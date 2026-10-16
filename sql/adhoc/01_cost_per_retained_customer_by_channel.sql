-- Question (Head of Growth, Q05): For customers who opened from January to May 2026, what did
-- each paid channel cost per new customer, and per customer still active three months later?
SELECT
    channel_name                                                        AS channel,
    sum(new_customers)                                                  AS new_customers,
    round(sum(spend) / sum(new_customers), 2)                           AS cost_per_new_customer,
    round(sum(m3_active_customers) * 100.0 / sum(new_customers), 1)     AS month3_active_pct,
    round(sum(spend) / sum(m3_active_customers), 2)                     AS cost_per_customer_active_in_month3
FROM kpi.channel_monthly
WHERE is_paid
  AND month_start BETWEEN DATE '2026-01-01' AND DATE '2026-05-01'
GROUP BY channel_name
ORDER BY cost_per_customer_active_in_month3 DESC
