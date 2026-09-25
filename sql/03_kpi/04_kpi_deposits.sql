-- Deposit KPIs by month. Cost of funds is interest accrued on the month's average balances,
-- annualised: interest / average deposits x 365 / days in month.
CREATE OR REPLACE TABLE kpi.deposits_monthly AS
WITH b AS (
    SELECT
        month_start,
        max(month_end_date)                                             AS month_end_date,
        sum(balance) FILTER (WHERE product_family = 'CASA')             AS casa_balance,
        sum(balance) FILTER (WHERE product_family = 'FD')               AS fd_balance,
        coalesce(sum(balance) FILTER (WHERE is_promo_fd), 0)            AS promo_fd_balance,
        sum(balance)                                                    AS total_deposits,
        sum(average_balance)                                            AS average_deposits,
        sum(interest_accrued)                                           AS interest_expense
    FROM marts.fct_account_balances_monthly
    GROUP BY 1
),
placements AS (
    SELECT posting_month AS month_start, sum(amount) AS fd_placed
    FROM marts.fct_ledger_postings
    WHERE product_family = 'FD' AND txn_type = 'fd_placement'
    GROUP BY 1
)
SELECT
    b.month_start,
    b.casa_balance,
    b.fd_balance,
    b.promo_fd_balance,
    b.total_deposits,
    b.casa_balance / b.total_deposits                                   AS casa_ratio,
    b.average_deposits,
    b.interest_expense,
    b.interest_expense / b.average_deposits * 365 / day(b.month_end_date) AS cost_of_funds,
    coalesce(p.fd_placed, 0)                                            AS fd_placed
FROM b
LEFT JOIN placements AS p ON p.month_start = b.month_start;

-- What happened to fixed deposit money at maturity: rolled over, kept in savings, or
-- transferred out of the bank within 30 days.
CREATE OR REPLACE TABLE kpi.fd_maturity_outcomes AS
WITH matured AS (
    SELECT
        a.account_id,
        a.customer_id,
        a.is_promo_fd,
        a.maturity_date,
        -p.amount                                                       AS matured_amount,
        p.txn_type = 'fd_rollover'                                      AS rolled_over
    FROM marts.dim_account AS a
    JOIN marts.fct_ledger_postings AS p
      ON p.account_id = a.account_id
     AND p.txn_type IN ('fd_maturity', 'fd_rollover')
     AND p.amount < 0
    WHERE a.product_family = 'FD'
),
outflows AS (   -- transfers out of the customer's savings in the 30 days after maturity
    SELECT
        m.account_id,
        coalesce(-sum(p.amount), 0)                                     AS transferred_out_30d
    FROM matured AS m
    JOIN marts.dim_customer AS c ON c.customer_id = m.customer_id
    LEFT JOIN marts.fct_ledger_postings AS p
           ON p.account_id = c.savings_account_id
          AND p.txn_type = 'duitnow_out'
          AND p.posting_date > m.maturity_date
          AND p.posting_date <= m.maturity_date + 30
    WHERE NOT m.rolled_over
    GROUP BY 1
)
SELECT
    m.account_id,
    m.customer_id,
    m.is_promo_fd,
    m.maturity_date,
    CAST(date_trunc('month', m.maturity_date) AS DATE)                  AS maturity_month,
    m.matured_amount,
    m.rolled_over,
    CASE WHEN m.rolled_over THEN 0 ELSE least(o.transferred_out_30d, m.matured_amount) END AS left_within_30d,
    m.matured_amount
        - CASE WHEN m.rolled_over THEN 0 ELSE least(o.transferred_out_30d, m.matured_amount) END AS retained_30d,
    m.maturity_date + 30 <= DATE '2026-08-31'                           AS window_complete
FROM matured AS m
LEFT JOIN outflows AS o ON o.account_id = m.account_id;
