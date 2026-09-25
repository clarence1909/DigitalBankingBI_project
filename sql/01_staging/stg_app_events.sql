-- Mobile app events: one row per event.
-- Cleaning rules:
--   * The app retries sends, so an event can arrive twice: keep the first copy received.
--   * Timestamps arrive in UTC ('...Z') or, from the old Android app, as local time with an
--     offset ('...+08:00'). Both parse to the same instant; reporting uses Malaysia time.
--   * Channel labels differ between SDK versions: mapped through reference.channel_map.
--   * The eKYC flow flag only exists from the A/B test onwards; before it, everyone saw the
--     control flow, so a missing flag means control.
CREATE OR REPLACE TABLE staging.stg_app_events AS
WITH typed AS (
    SELECT
        trim(event_id)                                              AS event_id,
        lower(trim(event_name))                                     AS event_name,
        CAST(event_ts AS TIMESTAMPTZ)                               AS event_ts_utc,
        CAST(received_at AS TIMESTAMPTZ)                            AS received_at_utc,
        trim(applicant_id)                                          AS applicant_id,
        json_extract_string(context, '$.channel')                   AS channel_raw,
        lower(trim(json_extract_string(context, '$.device_os')))    AS device_os,
        json_extract_string(context, '$.app_version')               AS app_version,
        json_extract_string(properties, '$.ekyc_flow')              AS ekyc_flow_raw,
        TRY_CAST(json_extract_string(properties, '$.attempt') AS INTEGER) AS attempt,
        json_extract_string(properties, '$.reason')                 AS reason,
        json_extract_string(properties, '$.customer_id')            AS customer_id
    FROM raw.app_events
)
SELECT
    t.event_id,
    t.event_name,
    t.event_ts_utc,
    t.event_ts_utc AT TIME ZONE 'Asia/Kuala_Lumpur'                 AS event_ts_myt,
    CAST(t.event_ts_utc AT TIME ZONE 'Asia/Kuala_Lumpur' AS DATE)   AS event_date,
    t.received_at_utc,
    t.applicant_id,
    t.channel_raw,
    cm.channel,
    t.device_os,
    t.app_version,
    coalesce(t.ekyc_flow_raw, 'control')                            AS ekyc_flow,
    t.ekyc_flow_raw IS NOT NULL                                     AS has_experiment_flag,
    t.attempt,
    t.reason,
    t.customer_id
FROM typed AS t
LEFT JOIN reference.channel_map AS cm
    ON cm.raw_label = lower(trim(t.channel_raw))
QUALIFY row_number() OVER (PARTITION BY t.event_id ORDER BY t.received_at_utc) = 1;
