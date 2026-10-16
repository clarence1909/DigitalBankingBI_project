-- Personal financing originations from the loan management system.
CREATE OR REPLACE TABLE staging.stg_loans AS
SELECT
    trim(l.loan_id)                                                 AS loan_id,
    trim(l.customer_id)                                             AS customer_id,
    CAST(l.application_date AS DATE)                                AS application_date,
    CAST(l.disbursement_date AS DATE)                               AS disbursement_date,
    CAST(l.principal AS DECIMAL(18, 2))                             AS principal,
    CAST(l.tenor_months AS INTEGER)                                 AS tenor_months,
    CAST(l.interest_rate_pct AS DECIMAL(6, 2))                      AS interest_rate_pct,
    upper(trim(l.risk_grade))                                       AS risk_grade,
    trim(l.credit_policy_code)                                      AS credit_policy_code,
    cp.credit_policy,
    cp.policy_name,
    CAST(l.dsr_pct AS DECIMAL(6, 2))                                AS dsr_pct
FROM raw.loans AS l
LEFT JOIN reference.credit_policy_map AS cp
    ON cp.credit_policy_code = trim(l.credit_policy_code);
