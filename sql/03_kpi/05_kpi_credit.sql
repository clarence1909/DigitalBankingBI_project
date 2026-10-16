-- Personal financing KPIs by month.
CREATE OR REPLACE TABLE kpi.credit_monthly AS
WITH months AS (SELECT DISTINCT month_start FROM marts.dim_date WHERE month_start >= DATE '2025-01-01'),
book AS (
    SELECT
        month_start,
        count(*) FILTER (WHERE is_on_book)                              AS loans_on_book,
        sum(outstanding_principal) FILTER (WHERE is_on_book)            AS gross_loans,
        coalesce(sum(outstanding_principal) FILTER (WHERE is_30plus), 0) AS balance_30plus,
        coalesce(sum(outstanding_principal) FILTER (WHERE is_impaired), 0) AS balance_impaired,
        sum(written_off_amount)                                         AS written_off,
        sum(interest_income_accrued)                                    AS interest_income
    FROM marts.fct_loan_status_monthly
    GROUP BY 1
),
new_loans AS (
    SELECT CAST(date_trunc('month', disbursement_date) AS DATE) AS month_start,
           count(*) AS loans_disbursed, sum(principal) AS amount_disbursed
    FROM staging.stg_loans
    GROUP BY 1
),
early AS (   -- loans disbursed six months earlier that have ever been 30+ days past due
    SELECT vintage_month + INTERVAL 6 MONTH AS month_start,
           avg(CASE WHEN ever_30plus THEN 1.0 ELSE 0.0 END) AS early_delinquency_mob6
    FROM marts.fct_loan_status_monthly
    WHERE months_on_book = 6
    GROUP BY 1
)
SELECT
    m.month_start,
    b.loans_on_book,
    b.gross_loans,
    coalesce(n.loans_disbursed, 0)                                      AS loans_disbursed,
    coalesce(n.amount_disbursed, 0)                                     AS amount_disbursed,
    b.balance_30plus / b.gross_loans                                    AS par30,
    b.balance_impaired / b.gross_loans                                  AS gil_ratio,
    b.written_off,
    b.interest_income,
    e.early_delinquency_mob6
FROM months AS m
LEFT JOIN book AS b ON b.month_start = m.month_start
LEFT JOIN new_loans AS n ON n.month_start = m.month_start
LEFT JOIN early AS e ON CAST(e.month_start AS DATE) = m.month_start;

-- Vintage curves: share of each monthly vintage that has ever been 30+ days past due by each
-- month on book. Loans that settled or were written off still count, with their history.
CREATE OR REPLACE TABLE kpi.vintage_curves AS
WITH loans AS (
    SELECT DISTINCT loan_id, vintage_month, credit_policy FROM marts.fct_loan_status_monthly
),
grid AS (
    SELECT l.loan_id, l.vintage_month, l.credit_policy, CAST(r.range AS INTEGER) AS months_on_book
    FROM loans AS l
    CROSS JOIN range(0, 21) AS r
    WHERE l.vintage_month + to_months(CAST(r.range AS INTEGER)) <= DATE '2026-08-01'
),
ever AS (
    SELECT
        g.loan_id, g.vintage_month, g.credit_policy, g.months_on_book,
        coalesce(bool_or(s.days_past_due >= 30), false)                 AS ever_30plus
    FROM grid AS g
    LEFT JOIN marts.fct_loan_status_monthly AS s
           ON s.loan_id = g.loan_id AND s.months_on_book <= g.months_on_book
    GROUP BY 1, 2, 3, 4
)
SELECT
    vintage_month,
    credit_policy,
    months_on_book,
    count(*)                                                            AS loans,
    count(*) FILTER (WHERE ever_30plus)                                 AS ever_30plus_loans,
    avg(CASE WHEN ever_30plus THEN 1.0 ELSE 0.0 END)                    AS ever_30plus_rate
FROM ever
GROUP BY 1, 2, 3;

-- Roll rates: how loans move between delinquency buckets from one month end to the next.
CREATE OR REPLACE TABLE kpi.roll_rates AS
WITH t AS (
    SELECT
        loan_id,
        month_start,
        dpd_bucket AS from_bucket,
        lead(dpd_bucket) OVER (PARTITION BY loan_id ORDER BY month_start) AS to_bucket,
        lead(month_start) OVER (PARTITION BY loan_id ORDER BY month_start) AS next_month
    FROM marts.fct_loan_status_monthly
)
SELECT
    next_month                                                          AS month_start,
    from_bucket,
    to_bucket,
    count(*)                                                            AS loans
FROM t
WHERE to_bucket IS NOT NULL AND from_bucket NOT IN ('Settled', 'Written off')
GROUP BY 1, 2, 3;
