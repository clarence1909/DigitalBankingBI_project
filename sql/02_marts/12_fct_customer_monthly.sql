-- One row per customer per month from the month they opened (periodic snapshot of
-- behaviour). A customer is active in a month if they made at least one transaction
-- themselves: a transfer out, a bill payment, a card purchase or an FD placement.
CREATE OR REPLACE TABLE marts.fct_customer_monthly AS
WITH months AS (
    SELECT DISTINCT month_start FROM marts.dim_date
),
grid AS (
    SELECT c.customer_id, c.cohort_month, m.month_start
    FROM marts.dim_customer AS c
    JOIN months AS m
      ON m.month_start >= c.cohort_month
     AND (c.closed_date IS NULL OR m.month_start <= date_trunc('month', c.closed_date))
),
txn AS (
    SELECT
        customer_id,
        posting_month                                                   AS month_start,
        count(*) FILTER (WHERE is_customer_initiated)                   AS customer_txns,
        count(*) FILTER (WHERE txn_type = 'card_purchase')              AS card_txns,
        coalesce(-sum(amount) FILTER (WHERE txn_type = 'card_purchase'), 0) AS card_spend,
        coalesce(-sum(amount) FILTER (WHERE txn_type IN ('duitnow_out', 'bill_payment')), 0) AS transfers_and_bills_out,
        coalesce(sum(amount) FILTER (WHERE txn_type = 'salary'), 0)     AS salary_in,
        coalesce(sum(amount) FILTER (WHERE txn_type = 'duitnow_in'), 0) AS transfers_in
    FROM marts.fct_ledger_postings
    WHERE product_family = 'CASA'
    GROUP BY 1, 2
),
bal AS (
    SELECT
        customer_id,
        month_start,
        coalesce(sum(balance) FILTER (WHERE product_family = 'CASA'), 0) AS casa_balance,
        coalesce(sum(balance) FILTER (WHERE product_family = 'FD'), 0)   AS fd_balance
    FROM marts.fct_account_balances_monthly
    GROUP BY 1, 2
)
SELECT
    g.customer_id,
    g.cohort_month,
    g.month_start,
    date_diff('month', g.cohort_month, g.month_start)                   AS months_since_open,
    coalesce(t.customer_txns, 0)                                        AS customer_txns,
    coalesce(t.customer_txns, 0) > 0                                    AS is_active,
    coalesce(t.card_txns, 0)                                            AS card_txns,
    coalesce(t.card_spend, 0)                                           AS card_spend,
    coalesce(t.transfers_and_bills_out, 0)                              AS transfers_and_bills_out,
    coalesce(t.salary_in, 0)                                            AS salary_in,
    coalesce(t.transfers_in, 0)                                         AS transfers_in,
    coalesce(b.casa_balance, 0)                                         AS casa_balance,
    coalesce(b.fd_balance, 0)                                           AS fd_balance
FROM grid AS g
LEFT JOIN txn AS t ON t.customer_id = g.customer_id AND t.month_start = g.month_start
LEFT JOIN bal AS b ON b.customer_id = g.customer_id AND b.month_start = g.month_start;
