-- Core banking accounts: savings (CASA), fixed deposits and debit cards.
-- Cleaning rules:
--   * Product codes vary in format (SAV-01, SAV01, sav-01): mapped through reference.product_map.
--   * Empty strings are missing values.
CREATE OR REPLACE TABLE staging.stg_accounts AS
SELECT
    trim(a.account_id)                                              AS account_id,
    trim(a.customer_id)                                             AS customer_id,
    upper(trim(a.product_code))                                     AS product_code_raw,
    pm.product_code,
    pm.product_family,
    CAST(nullif(trim(a.open_date), '') AS DATE)                     AS open_date,
    CAST(nullif(trim(a.close_date), '') AS DATE)                    AS close_date,
    upper(trim(a.account_status))                                   AS account_status,
    TRY_CAST(a.interest_rate_pct AS DECIMAL(6, 2))                  AS interest_rate_pct,
    TRY_CAST(a.principal AS DECIMAL(18, 2))                         AS fd_principal,
    TRY_CAST(a.tenor_months AS INTEGER)                             AS tenor_months,
    CAST(nullif(trim(a.maturity_date), '') AS DATE)                 AS maturity_date,
    nullif(trim(a.campaign_code), '')                               AS campaign_code,
    nullif(trim(a.rollover_of_account_id), '')                      AS rollover_of_account_id,
    nullif(trim(a.linked_account_id), '')                           AS linked_account_id,
    CAST(nullif(trim(a.activation_date), '') AS DATE)               AS card_activation_date
FROM raw.accounts AS a
LEFT JOIN reference.product_map AS pm
    ON pm.raw_code = upper(trim(a.product_code));
