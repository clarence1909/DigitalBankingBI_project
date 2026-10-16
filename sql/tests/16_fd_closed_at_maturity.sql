-- name: fd_empty_after_maturity
-- severity: error
-- description: A matured fixed deposit has a zero balance from its maturity month on.
-- break: UPDATE marts.fct_account_balances_monthly SET balance = 100 WHERE account_id = (SELECT min(account_id) FROM marts.dim_account WHERE product_family = 'FD' AND account_status = 'MATURED') AND month_start = (SELECT date_trunc('month', maturity_date) FROM marts.dim_account WHERE account_id = (SELECT min(account_id) FROM marts.dim_account WHERE product_family = 'FD' AND account_status = 'MATURED'))
SELECT b.account_id, b.month_end_date, b.balance
FROM marts.fct_account_balances_monthly AS b
JOIN marts.dim_account AS a ON a.account_id = b.account_id
WHERE a.product_family = 'FD'
  AND a.account_status = 'MATURED'
  AND b.month_start >= date_trunc('month', a.maturity_date)
  AND b.balance <> 0
