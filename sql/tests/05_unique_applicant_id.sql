-- name: unique_applicant_id
-- severity: error
-- description: The onboarding funnel has one row per applicant.
-- break: INSERT INTO marts.fct_onboarding_funnel SELECT * FROM marts.fct_onboarding_funnel LIMIT 1
SELECT applicant_id, count(*) AS copies
FROM marts.fct_onboarding_funnel
GROUP BY applicant_id
HAVING count(*) > 1
