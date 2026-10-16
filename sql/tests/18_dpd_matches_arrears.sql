-- name: dpd_matches_arrears
-- severity: error
-- description: An active loan is past due exactly when it has instalments in arrears.
-- break: UPDATE marts.fct_loan_status_monthly SET days_past_due = 45 WHERE loan_id = 'PF00000001' AND months_on_book = 0
SELECT loan_id, month_end_date, days_past_due, instalments_in_arrears
FROM marts.fct_loan_status_monthly
WHERE loan_status = 'ACTIVE'
  AND ((days_past_due > 0) <> (instalments_in_arrears > 0))
