-- Month-end loan tape: one row per loan per month it was on the books.
CREATE OR REPLACE TABLE staging.stg_loan_tape AS
SELECT
    trim(loan_id)                                                   AS loan_id,
    CAST(snapshot_date AS DATE)                                     AS snapshot_date,
    CAST(outstanding_principal AS DECIMAL(18, 2))                   AS outstanding_principal,
    CAST(instalments_due AS INTEGER)                                AS instalments_due,
    CAST(instalments_paid AS INTEGER)                               AS instalments_paid,
    CAST(days_past_due AS INTEGER)                                  AS days_past_due,
    upper(trim(loan_status))                                        AS loan_status
FROM raw.loan_tape;
