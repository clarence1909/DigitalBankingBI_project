-- Question (Treasurer, Q14): How much of the money placed in the Raya FD promotion came out of
-- customers' own Kelip savings, and how much was new money brought in from other banks?
-- New money = transfers into the customer's savings in the three hours before the placement.
WITH placements AS (
    SELECT p.account_id AS fd_account_id, a.customer_id, p.posting_ts_myt, p.amount AS placed
    FROM marts.fct_ledger_postings AS p
    JOIN marts.dim_account AS a ON a.account_id = p.account_id
    WHERE a.is_promo_fd AND p.txn_type = 'fd_placement'
),
new_money AS (
    SELECT pl.fd_account_id, coalesce(sum(t.amount), 0) AS transferred_in
    FROM placements AS pl
    JOIN marts.dim_customer AS c ON c.customer_id = pl.customer_id
    LEFT JOIN marts.fct_ledger_postings AS t
           ON t.account_id = c.savings_account_id
          AND t.txn_type = 'duitnow_in'
          AND t.posting_ts_myt BETWEEN pl.posting_ts_myt - INTERVAL 3 HOUR AND pl.posting_ts_myt
    GROUP BY 1
)
SELECT
    count(*)                                                            AS promo_placements,
    round(sum(pl.placed), 2)                                            AS total_placed,
    round(sum(least(n.transferred_in, pl.placed)), 2)                   AS new_money,
    round(sum(pl.placed) - sum(least(n.transferred_in, pl.placed)), 2)  AS from_existing_savings,
    round(100 - sum(least(n.transferred_in, pl.placed)) * 100.0 / sum(pl.placed), 1) AS pct_from_existing_savings
FROM placements AS pl
JOIN new_money AS n ON n.fd_account_id = pl.fd_account_id
