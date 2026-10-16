-- name: unique_auth_id
-- severity: error
-- description: Each card authorisation appears once after status updates and resends are resolved.
-- break: INSERT INTO marts.fct_card_authorisations SELECT * FROM marts.fct_card_authorisations LIMIT 1
SELECT auth_id, count(*) AS copies
FROM marts.fct_card_authorisations
GROUP BY auth_id
HAVING count(*) > 1
