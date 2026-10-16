-- name: no_orphan_accounts
-- severity: error
-- description: Every account belongs to a known customer.
-- break: UPDATE marts.dim_account SET customer_id = 'C9999999' WHERE account_id = (SELECT min(account_id) FROM marts.dim_account)
SELECT a.account_id, a.customer_id
FROM marts.dim_account AS a
LEFT JOIN marts.dim_customer AS c ON c.customer_id = a.customer_id
WHERE c.customer_id IS NULL
