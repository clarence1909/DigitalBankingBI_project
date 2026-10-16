-- Customers, with acquisition details from the app and the debit card from core banking.
CREATE OR REPLACE TABLE marts.dim_customer AS
WITH card AS (
    SELECT customer_id, account_id AS card_id, card_activation_date
    FROM staging.stg_accounts
    WHERE product_family = 'CARD'
),
casa AS (
    SELECT customer_id, account_id AS savings_account_id, close_date
    FROM staging.stg_accounts
    WHERE product_family = 'CASA'
)
SELECT
    c.customer_id,
    c.applicant_id,
    c.open_date,
    CAST(date_trunc('month', c.open_date) AS DATE)                      AS cohort_month,
    f.acquisition_channel,
    f.ekyc_flow,
    f.device_os,
    c.state,
    c.employment_type,
    c.income_band,
    c.risk_rating,
    year(c.open_date) - c.birth_year                                    AS age_at_open,
    CASE
        WHEN year(c.open_date) - c.birth_year < 25 THEN '18-24'
        WHEN year(c.open_date) - c.birth_year < 35 THEN '25-34'
        WHEN year(c.open_date) - c.birth_year < 45 THEN '35-44'
        WHEN year(c.open_date) - c.birth_year < 55 THEN '45-54'
        ELSE '55+'
    END                                                                 AS age_band,
    casa.savings_account_id,
    card.card_id,
    card.card_id IS NOT NULL                                            AS has_debit_card,
    card.card_activation_date,
    coalesce(card.card_activation_date <= c.open_date + 30, false)      AS card_activated_30d,
    c.fraud_flag_date,
    coalesce(c.fraud_flag_date <= c.open_date + 30, false)              AS fraud_flagged_30d,
    c.customer_status,
    casa.close_date                                                     AS closed_date
FROM staging.stg_customers AS c
LEFT JOIN marts.fct_onboarding_funnel AS f ON f.applicant_id = c.applicant_id
LEFT JOIN card ON card.customer_id = c.customer_id
LEFT JOIN casa ON casa.customer_id = c.customer_id;
