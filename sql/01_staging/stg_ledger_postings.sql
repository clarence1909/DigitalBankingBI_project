-- Ledger postings from the posting engine.
-- Cleaning rules:
--   * Timestamps are UTC; month-end cut-off is Malaysia time, so a posting at 18:00 UTC on
--     the last day of a month belongs to the next month in Malaysia.
--   * The posting engine was upgraded on 1 Jun 2025 and switched from long transaction
--     codes (DUITNOW_OUT) to short ones (DNO): both map through reference.txn_code_map.
--   * Amounts are unsigned with a CR/DR direction; signed_amount is + for credits.
CREATE OR REPLACE TABLE staging.stg_ledger_postings AS
SELECT
    trim(p.posting_id)                                              AS posting_id,
    trim(p.account_id)                                              AS account_id,
    CAST(p.posting_ts AS TIMESTAMPTZ)                               AS posting_ts_utc,
    CAST(p.posting_ts AS TIMESTAMPTZ) AT TIME ZONE 'Asia/Kuala_Lumpur' AS posting_ts_myt,
    CAST(CAST(p.posting_ts AS TIMESTAMPTZ) AT TIME ZONE 'Asia/Kuala_Lumpur' AS DATE) AS posting_date,
    CAST(p.amount AS DECIMAL(18, 2))                                AS amount,
    upper(trim(p.direction))                                        AS direction,
    CASE upper(trim(p.direction)) WHEN 'CR' THEN 1 WHEN 'DR' THEN -1 END
        * CAST(p.amount AS DECIMAL(18, 2))                          AS signed_amount,
    upper(trim(p.txn_code))                                         AS txn_code_raw,
    tm.txn_type,
    tm.is_customer_initiated,
    upper(trim(p.channel))                                          AS channel,
    nullif(trim(p.reference), '')                                   AS reference
FROM raw.ledger_postings AS p
LEFT JOIN reference.txn_code_map AS tm
    ON tm.txn_code_raw = upper(trim(p.txn_code));
