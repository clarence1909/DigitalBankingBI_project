-- name: unique_posting_id
-- severity: error
-- description: Each ledger posting appears once.
-- break: INSERT INTO marts.fct_ledger_postings SELECT * FROM marts.fct_ledger_postings LIMIT 1
SELECT posting_id, count(*) AS copies
FROM marts.fct_ledger_postings
GROUP BY posting_id
HAVING count(*) > 1
