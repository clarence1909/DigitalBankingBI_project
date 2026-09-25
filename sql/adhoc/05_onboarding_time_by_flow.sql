-- Question (Head of Onboarding, Q09): In 2026, how long did it take to open an account, and how
-- often did an application go to manual review, for each eKYC flow?
SELECT
    ekyc_flow,
    count(*) FILTER (WHERE is_opened)                                   AS accounts_opened,
    round(median(hours_to_open) FILTER (WHERE is_opened) * 60, 1)       AS median_minutes_to_open,
    round(quantile_cont(hours_to_open, 0.9) FILTER (WHERE is_opened), 1) AS p90_hours_to_open,
    round(avg(CASE WHEN went_to_manual_review THEN 100.0 ELSE 0 END)
          FILTER (WHERE ekyc_approved_ts IS NOT NULL), 1)               AS pct_manual_review,
    round(avg(liveness_failures) FILTER (WHERE id_scanned_ts IS NOT NULL), 2) AS avg_liveness_retries
FROM marts.fct_onboarding_funnel
WHERE signup_started_ts >= TIMESTAMP '2026-01-01'
GROUP BY ekyc_flow
ORDER BY ekyc_flow
