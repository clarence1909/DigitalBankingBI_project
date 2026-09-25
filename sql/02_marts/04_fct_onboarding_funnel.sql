-- Onboarding funnel: an accumulating snapshot with one row per applicant and a timestamp
-- for each step they reached (Malaysia time).
CREATE OR REPLACE TABLE marts.fct_onboarding_funnel AS
WITH per_applicant AS (
    SELECT
        applicant_id,
        arg_min(channel, event_ts_myt)                                              AS acquisition_channel,
        arg_min(device_os, event_ts_myt)                                            AS device_os,
        coalesce(max(CASE WHEN has_experiment_flag THEN ekyc_flow END), 'control')  AS ekyc_flow,
        min(event_ts_myt) FILTER (WHERE event_name = 'signup_started')              AS signup_started_ts,
        min(event_ts_myt) FILTER (WHERE event_name = 'phone_verified')              AS phone_verified_ts,
        min(event_ts_myt) FILTER (WHERE event_name = 'id_scanned')                  AS id_scanned_ts,
        min(event_ts_myt) FILTER (WHERE event_name = 'liveness_passed')             AS liveness_passed_ts,
        min(event_ts_myt) FILTER (WHERE event_name = 'ekyc_approved')               AS ekyc_approved_ts,
        min(event_ts_myt) FILTER (WHERE event_name = 'account_opened')              AS account_opened_ts,
        count(*) FILTER (WHERE event_name = 'liveness_failed')                      AS liveness_failures,
        bool_or(event_name = 'ekyc_rejected')                                       AS is_ekyc_rejected,
        max(customer_id)                                                            AS customer_id
    FROM staging.stg_app_events
    GROUP BY applicant_id
),
test AS (
    SELECT start_date, end_date FROM reference.experiments WHERE experiment_id = 'ekyc_guided_flow'
)
SELECT
    a.applicant_id,
    a.customer_id,
    a.acquisition_channel,
    a.device_os,
    a.ekyc_flow,
    CAST(a.signup_started_ts AS DATE) BETWEEN test.start_date AND test.end_date     AS is_in_ekyc_test,
    CAST(date_trunc('month', a.signup_started_ts) AS DATE)                          AS start_month,
    a.signup_started_ts,
    a.phone_verified_ts,
    a.id_scanned_ts,
    a.liveness_passed_ts,
    a.ekyc_approved_ts,
    a.account_opened_ts,
    a.liveness_failures,
    a.is_ekyc_rejected,
    CASE
        WHEN a.account_opened_ts IS NOT NULL THEN 6
        WHEN a.ekyc_approved_ts IS NOT NULL THEN 5
        WHEN a.liveness_passed_ts IS NOT NULL THEN 4
        WHEN a.id_scanned_ts IS NOT NULL THEN 3
        WHEN a.phone_verified_ts IS NOT NULL THEN 2
        ELSE 1
    END                                                                             AS furthest_step_no,
    a.account_opened_ts IS NOT NULL                                                 AS is_opened,
    a.ekyc_approved_ts - a.liveness_passed_ts > INTERVAL 1 HOUR                     AS went_to_manual_review,
    CAST(round(date_diff('second', a.signup_started_ts, a.account_opened_ts) / 3600.0, 2) AS DECIMAL(10, 2)) AS hours_to_open
FROM per_applicant AS a
CROSS JOIN test;
