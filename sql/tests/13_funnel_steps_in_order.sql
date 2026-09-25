-- name: funnel_steps_in_order
-- severity: error
-- description: Applicants pass the onboarding steps in order: each step needs the one before it, never earlier in time.
-- break: UPDATE marts.fct_onboarding_funnel SET phone_verified_ts = signup_started_ts - INTERVAL 1 HOUR WHERE applicant_id = 'A0000001'
SELECT applicant_id, furthest_step_no
FROM marts.fct_onboarding_funnel
WHERE (phone_verified_ts < signup_started_ts)
   OR (id_scanned_ts < phone_verified_ts)
   OR (liveness_passed_ts < id_scanned_ts)
   OR (ekyc_approved_ts < liveness_passed_ts)
   OR (account_opened_ts < ekyc_approved_ts)
   OR (phone_verified_ts IS NOT NULL AND signup_started_ts IS NULL)
   OR (id_scanned_ts IS NOT NULL AND phone_verified_ts IS NULL)
   OR (liveness_passed_ts IS NOT NULL AND id_scanned_ts IS NULL)
   OR (ekyc_approved_ts IS NOT NULL AND liveness_passed_ts IS NULL)
   OR (account_opened_ts IS NOT NULL AND ekyc_approved_ts IS NULL)
