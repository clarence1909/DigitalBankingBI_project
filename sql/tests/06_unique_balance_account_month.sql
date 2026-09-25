-- name: unique_balance_account_month
-- severity: error
-- description: Month-end balances have one row per account per month.
-- break: INSERT INTO marts.fct_account_balances_monthly SELECT * FROM marts.fct_account_balances_monthly LIMIT 1
SELECT account_id, month_end_date, count(*) AS copies
FROM marts.fct_account_balances_monthly
GROUP BY account_id, month_end_date
HAVING count(*) > 1
