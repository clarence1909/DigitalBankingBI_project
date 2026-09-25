-- name: unique_loan_month
-- severity: error
-- description: The loan status snapshot has one row per loan per month.
-- break: INSERT INTO marts.fct_loan_status_monthly SELECT * FROM marts.fct_loan_status_monthly LIMIT 1
SELECT loan_id, month_end_date, count(*) AS copies
FROM marts.fct_loan_status_monthly
GROUP BY loan_id, month_end_date
HAVING count(*) > 1
