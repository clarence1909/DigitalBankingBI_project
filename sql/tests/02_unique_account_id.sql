-- name: unique_account_id
-- severity: error
-- description: Each account appears once in dim_account.
-- break: INSERT INTO marts.dim_account SELECT * FROM marts.dim_account LIMIT 1
SELECT account_id, count(*) AS copies
FROM marts.dim_account
GROUP BY account_id
HAVING count(*) > 1
