-- name: no_negative_balances
-- severity: warn
-- description: Deposit accounts never close a month overdrawn (Kelip Bank offers no overdrafts).
-- break: UPDATE marts.fct_account_balances_monthly SET balance = -1 WHERE account_id = 'SA00000001' AND month_end_date = DATE '2024-09-30'
SELECT account_id, month_end_date, balance
FROM marts.fct_account_balances_monthly
WHERE balance < 0
