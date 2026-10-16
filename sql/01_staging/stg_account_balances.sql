-- Month-end ledger balances as reported by core banking (one row per account per month).
CREATE OR REPLACE TABLE staging.stg_account_balances AS
SELECT
    trim(account_id)                                                AS account_id,
    CAST(balance_date AS DATE)                                      AS balance_date,
    CAST(ledger_balance AS DECIMAL(18, 2))                          AS balance,
    upper(trim(currency))                                           AS currency
FROM raw.account_balances;
