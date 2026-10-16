-- name: no_orphan_loans
-- severity: error
-- description: Every loan belongs to a known customer.
-- break: UPDATE marts.fct_loan_status_monthly SET customer_id = 'C9999999' WHERE loan_id = 'PF00000001'
SELECT DISTINCT l.loan_id, l.customer_id
FROM marts.fct_loan_status_monthly AS l
LEFT JOIN marts.dim_customer AS c ON c.customer_id = l.customer_id
WHERE c.customer_id IS NULL
