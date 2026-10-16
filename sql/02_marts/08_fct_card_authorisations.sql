-- Card authorisations (transaction grain) with settlement timing.
CREATE OR REPLACE TABLE marts.fct_card_authorisations AS
SELECT
    c.auth_id,
    c.card_id,
    a.customer_id,
    c.auth_ts_myt,
    CAST(c.auth_ts_myt AS DATE)                                         AS auth_date,
    CAST(date_trunc('month', c.auth_ts_myt) AS DATE)                    AS auth_month,
    c.amount,
    c.mcc,
    c.merchant_category,
    c.category_group,
    c.entry_mode,
    c.response_code,
    r.response_description,
    c.status,
    c.response_code = '00'                                              AS was_approved,
    c.status = 'APPROVED'                                               AS is_approved_final,
    c.settlement_date,
    CAST(date_trunc('month', c.settlement_date) AS DATE)                AS settlement_month,
    date_diff('day', CAST(c.auth_ts_myt AS DATE), c.settlement_date)    AS settlement_lag_days,
    coalesce(date_diff('day', CAST(c.auth_ts_myt AS DATE), c.settlement_date) > 3, false) AS is_late_settlement
FROM staging.stg_card_authorisations AS c
LEFT JOIN marts.dim_account AS a ON a.account_id = c.card_id
LEFT JOIN reference.response_code_map AS r ON r.response_code = c.response_code;
