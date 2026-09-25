-- Card processor authorisations.
-- Cleaning rules:
--   * auth_ts is UTC with no offset: read it explicitly as UTC, then convert to Malaysia time.
--   * Status updates (for example a reversal) and resends arrive as extra rows for the same
--     auth_id: keep the latest record.
--   * Status, entry mode and merchant labels are inconsistent: statuses and entry modes map
--     through reference tables, and categories come from the MCC code, not the free-text label.
--   * settlement_date (YYYYMMDD) is the processor's business date; blank means not yet settled.
CREATE OR REPLACE TABLE staging.stg_card_authorisations AS
SELECT
    trim(c.auth_id)                                                 AS auth_id,
    trim(c.card_id)                                                 AS card_id,
    CAST(c.auth_ts AS TIMESTAMP) AT TIME ZONE 'UTC'                 AS auth_ts_utc,
    (CAST(c.auth_ts AS TIMESTAMP) AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Kuala_Lumpur' AS auth_ts_myt,
    CAST(c.amount AS DECIMAL(18, 2))                                AS amount,
    upper(trim(c.currency))                                         AS currency,
    TRY_CAST(c.mcc AS INTEGER)                                      AS mcc,
    mc.merchant_category,
    mc.category_group,
    trim(c.merchant_category)                                       AS merchant_category_raw,
    em.entry_mode,
    trim(c.entry_mode)                                              AS entry_mode_raw,
    trim(c.response_code)                                           AS response_code,
    sm.status,
    trim(c.status)                                                  AS status_raw,
    CAST(try_strptime(nullif(trim(c.settlement_date), ''), '%Y%m%d') AS DATE) AS settlement_date,
    CAST(c.record_updated_at AS TIMESTAMP)                          AS record_updated_at_utc
FROM raw.card_authorisations AS c
LEFT JOIN reference.merchant_category_map AS mc
    ON mc.mcc = TRY_CAST(c.mcc AS INTEGER)
LEFT JOIN reference.entry_mode_map AS em
    ON em.raw_entry_mode = upper(trim(c.entry_mode))
LEFT JOIN reference.card_status_map AS sm
    ON sm.raw_status = upper(trim(c.status))
QUALIFY row_number() OVER (PARTITION BY trim(c.auth_id)
                           ORDER BY CAST(c.record_updated_at AS TIMESTAMP) DESC) = 1;
