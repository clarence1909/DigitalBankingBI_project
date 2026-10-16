-- name: recon_ledger_to_balances
-- severity: error
-- description: Reconciliation 1: for every account and month, last month's balance plus the month's postings (Malaysia time) equals the balance core banking reports, to the sen.
-- break: UPDATE marts.fct_ledger_postings SET amount = amount - 0.01 WHERE posting_id = 'LP0000000001'
WITH flows AS (
    SELECT account_id, posting_month AS month_start, sum(amount) AS net_postings
    FROM marts.fct_ledger_postings
    WHERE product_family IN ('CASA', 'FD')
    GROUP BY 1, 2
),
tie AS (
    SELECT
        coalesce(b.account_id, f.account_id)                            AS account_id,
        coalesce(b.month_start, f.month_start)                          AS month_start,
        b.prior_balance,
        coalesce(f.net_postings, 0)                                     AS net_postings,
        b.balance                                                       AS reported_balance
    FROM marts.fct_account_balances_monthly AS b
    FULL OUTER JOIN flows AS f ON f.account_id = b.account_id AND f.month_start = b.month_start
)
SELECT account_id, month_start, prior_balance, net_postings, reported_balance,
       prior_balance + net_postings - reported_balance                  AS difference
FROM tie
WHERE reported_balance IS NULL
   OR prior_balance + net_postings <> reported_balance
