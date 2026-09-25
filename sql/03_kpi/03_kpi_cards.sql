-- Debit card KPIs by month, and spend by merchant category.
CREATE OR REPLACE TABLE kpi.cards_monthly AS
WITH months AS (SELECT DISTINCT month_start FROM marts.dim_date),
settled AS (   -- the finance view: purchases posted to the ledger in the month
    SELECT posting_month AS month_start, -sum(amount) AS card_spend, count(*) AS card_purchases
    FROM marts.fct_ledger_postings
    WHERE txn_type = 'card_purchase'
    GROUP BY 1
),
auths AS (
    SELECT
        auth_month                                                      AS month_start,
        count(*)                                                        AS authorisations,
        count(*) FILTER (WHERE was_approved)                            AS approved,
        count(*) FILTER (WHERE response_code = '51')                    AS declined_insufficient_funds,
        count(*) FILTER (WHERE response_code = '55')                    AS declined_wrong_pin,
        count(*) FILTER (WHERE response_code = '59')                    AS declined_suspected_fraud,
        count(DISTINCT customer_id) FILTER (WHERE is_approved_final)    AS active_cardholders
    FROM marts.fct_card_authorisations
    GROUP BY 1
),
activation AS (   -- a cohort is reported once every customer in it has had 30 days to activate
    SELECT cohort_month AS month_start,
           avg(CASE WHEN card_activated_30d THEN 1.0 ELSE 0.0 END)      AS card_activation_30d
    FROM marts.dim_customer
    WHERE has_debit_card
    GROUP BY 1
    HAVING max(open_date) + INTERVAL 30 DAY <= (SELECT max(date_day) FROM marts.dim_date)
)
SELECT
    m.month_start,
    s.card_spend,
    s.card_purchases,
    a.authorisations,
    a.approved,
    a.approved * 1.0 / a.authorisations                                 AS card_approval_rate,
    a.declined_insufficient_funds,
    a.declined_wrong_pin,
    a.declined_suspected_fraud,
    a.active_cardholders,
    act.card_activation_30d
FROM months AS m
LEFT JOIN settled AS s ON s.month_start = m.month_start
LEFT JOIN auths AS a ON a.month_start = m.month_start
LEFT JOIN activation AS act ON act.month_start = m.month_start;

CREATE OR REPLACE TABLE kpi.card_categories_monthly AS
SELECT
    auth_month                                                          AS month_start,
    category_group,
    merchant_category,
    count(*)                                                            AS purchases,
    sum(amount)                                                         AS spend
FROM marts.fct_card_authorisations
WHERE is_approved_final
GROUP BY 1, 2, 3;
