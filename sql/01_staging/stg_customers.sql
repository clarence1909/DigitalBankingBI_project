-- Core banking customers.
-- Cleaning rules:
--   * Dates come as DD/MM/YYYY.
--   * A re-extract left some customers in the file twice: keep the most recently updated row.
--   * State and employment labels are free text in places: mapped through reference tables.
CREATE OR REPLACE TABLE staging.stg_customers AS
SELECT
    trim(c.customer_id)                                             AS customer_id,
    trim(c.applicant_id)                                            AS applicant_id,
    CAST(strptime(trim(c.open_date), '%d/%m/%Y') AS DATE)           AS open_date,
    TRY_CAST(c.birth_year AS INTEGER)                               AS birth_year,
    trim(c.state)                                                   AS state_raw,
    sm.state,
    trim(c.employment_type)                                         AS employment_type_raw,
    em.employment_type,
    trim(c.monthly_income_band)                                     AS income_band,
    lower(trim(c.risk_rating))                                      AS risk_rating,
    CAST(try_strptime(nullif(trim(c.fraud_flag_date), ''), '%d/%m/%Y') AS DATE) AS fraud_flag_date,
    upper(trim(c.customer_status))                                  AS customer_status,
    CAST(c.last_updated_at AS TIMESTAMP)                            AS last_updated_at_utc
FROM raw.customers AS c
LEFT JOIN reference.state_map AS sm
    ON sm.raw_label = lower(trim(c.state))
LEFT JOIN reference.employment_map AS em
    ON em.raw_label = lower(trim(c.employment_type))
QUALIFY row_number() OVER (PARTITION BY trim(c.customer_id)
                           ORDER BY CAST(c.last_updated_at AS TIMESTAMP) DESC) = 1;
