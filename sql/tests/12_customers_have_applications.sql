-- name: customers_have_applications
-- severity: error
-- description: Every customer can be traced back to their sign-up in the app.
-- break: DELETE FROM marts.fct_onboarding_funnel WHERE applicant_id = (SELECT min(applicant_id) FROM marts.dim_customer)
SELECT c.customer_id, c.applicant_id
FROM marts.dim_customer AS c
LEFT JOIN marts.fct_onboarding_funnel AS f ON f.applicant_id = c.applicant_id
WHERE f.applicant_id IS NULL
