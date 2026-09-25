-- Personal financing month-end status (periodic snapshot), with delinquency buckets.
-- Impaired means more than 90 days past due, in line with Bank Negara Malaysia's
-- classification of impaired loans.
CREATE OR REPLACE TABLE marts.fct_loan_status_monthly AS
SELECT
    t.loan_id,
    l.customer_id,
    t.snapshot_date                                                     AS month_end_date,
    CAST(date_trunc('month', t.snapshot_date) AS DATE)                  AS month_start,
    CAST(date_trunc('month', l.disbursement_date) AS DATE)              AS vintage_month,
    l.credit_policy,
    l.policy_name,
    l.risk_grade,
    l.principal,
    l.interest_rate_pct,
    l.tenor_months,
    date_diff('month', date_trunc('month', l.disbursement_date), date_trunc('month', t.snapshot_date)) AS months_on_book,
    t.outstanding_principal,
    t.instalments_due,
    t.instalments_paid,
    t.instalments_due - t.instalments_paid                              AS instalments_in_arrears,
    t.days_past_due,
    CASE
        WHEN t.loan_status = 'SETTLED' THEN 'Settled'
        WHEN t.loan_status = 'WRITTEN_OFF' THEN 'Written off'
        WHEN t.days_past_due = 0 THEN 'Current'
        WHEN t.days_past_due < 30 THEN '1-29'
        WHEN t.days_past_due < 60 THEN '30-59'
        WHEN t.days_past_due <= 90 THEN '60-90'
        ELSE '90+'
    END                                                                 AS dpd_bucket,
    t.loan_status,
    t.loan_status = 'ACTIVE'                                            AS is_on_book,
    t.loan_status = 'ACTIVE' AND t.days_past_due >= 30                  AS is_30plus,
    t.loan_status = 'ACTIVE' AND t.days_past_due > 90                   AS is_impaired,
    bool_or(t.days_past_due >= 30) OVER (PARTITION BY t.loan_id ORDER BY t.snapshot_date) AS ever_30plus,
    CASE WHEN t.loan_status = 'WRITTEN_OFF' THEN t.outstanding_principal ELSE 0 END AS written_off_amount,
    CAST(CASE WHEN t.loan_status = 'ACTIVE' AND t.days_past_due <= 90
              THEN round(t.outstanding_principal * l.interest_rate_pct / 100 / 12, 2) ELSE 0 END
         AS DECIMAL(18, 2))                                             AS interest_income_accrued
FROM staging.stg_loan_tape AS t
JOIN staging.stg_loans AS l ON l.loan_id = t.loan_id;
