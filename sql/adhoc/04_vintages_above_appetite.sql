-- Question (Head of Credit Risk, Q19): Which monthly vintages have had more than 5% of loans
-- 30+ days past due by month 6 on book, and which credit policy approved them?
SELECT
    strftime(vintage_month, '%Y-%m')                                    AS vintage,
    credit_policy,
    loans,
    ever_30plus_loans,
    round(ever_30plus_rate * 100, 1)                                    AS pct_ever_30plus_by_month6
FROM kpi.vintage_curves
WHERE months_on_book = 6
  AND ever_30plus_rate > 0.05
ORDER BY vintage_month
