-- name: no_orphan_postings
-- severity: error
-- description: Every ledger posting is on a known account.
-- break: UPDATE marts.fct_ledger_postings SET account_id = 'SA99999999' WHERE posting_id = 'LP0000000001'
SELECT p.posting_id, p.account_id
FROM marts.fct_ledger_postings AS p
LEFT JOIN marts.dim_account AS a ON a.account_id = p.account_id
WHERE a.account_id IS NULL
