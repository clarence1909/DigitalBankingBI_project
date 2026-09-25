-- Month-end deposit balances (periodic snapshot) with the rate that applied and the interest
-- accrued on the month's average balance, which is what cost of funds is built from.
CREATE OR REPLACE TABLE marts.fct_account_balances_monthly AS
WITH b AS (
    SELECT
        s.account_id,
        s.balance_date                                                  AS month_end_date,
        CAST(date_trunc('month', s.balance_date) AS DATE)               AS month_start,
        s.balance,
        coalesce(lag(s.balance) OVER (PARTITION BY s.account_id ORDER BY s.balance_date), 0) AS prior_balance
    FROM staging.stg_account_balances AS s
)
SELECT
    b.account_id,
    a.customer_id,
    a.product_code,
    a.product_family,
    a.is_promo_fd,
    b.month_start,
    b.month_end_date,
    b.balance,
    b.prior_balance,
    CAST((b.balance + b.prior_balance) / 2 AS DECIMAL(18, 3))          AS average_balance,
    CASE WHEN a.product_family = 'CASA' THEN r.rate_pct ELSE a.fd_rate_pct END AS interest_rate_pct,
    -- Money is stored as exact decimals, so totals are the same on every run and machine
    CAST(round((b.balance + b.prior_balance) / 2
          * CASE WHEN a.product_family = 'CASA' THEN r.rate_pct ELSE a.fd_rate_pct END / 100
          * day(b.month_end_date) / 365, 2) AS DECIMAL(18, 2))          AS interest_accrued
FROM b
JOIN marts.dim_account AS a ON a.account_id = b.account_id
LEFT JOIN reference.product_rates AS r
    ON a.product_family = 'CASA'
   AND r.product_code = a.product_code
   AND b.month_end_date BETWEEN r.effective_from AND r.effective_to;
