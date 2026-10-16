-- Net interest income by month (accrual basis): interest earned on performing financing,
-- less interest accrued on deposits.
CREATE OR REPLACE TABLE kpi.finance_monthly AS
SELECT
    d.month_start,
    coalesce(c.interest_income, 0)                                      AS loan_interest_income,
    d.interest_expense                                                  AS deposit_interest_expense,
    coalesce(c.interest_income, 0) - d.interest_expense                 AS net_interest_income
FROM kpi.deposits_monthly AS d
LEFT JOIN kpi.credit_monthly AS c ON c.month_start = d.month_start;
