-- name: late_card_settlements
-- severity: info
-- description: Card purchases that settled more than three days after authorisation, and those that settled in a later month, by authorisation month. These explain timing differences when card spend is compared by authorisation month instead of settlement month.
SELECT
    auth_month,
    count(*) FILTER (WHERE is_late_settlement)                          AS late_settlements,
    count(*) FILTER (WHERE settlement_month > auth_month)               AS settled_next_month,
    sum(amount) FILTER (WHERE settlement_month > auth_month)            AS amount_settled_next_month
FROM marts.fct_card_authorisations
WHERE status = 'APPROVED' AND settlement_date IS NOT NULL
GROUP BY 1
