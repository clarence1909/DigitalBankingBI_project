-- name: no_orphan_card_authorisations
-- severity: error
-- description: Every card authorisation is on a card issued by Kelip Bank.
-- break: UPDATE marts.fct_card_authorisations SET card_id = 'DC99999999' WHERE auth_id = 'AU0000000001'
SELECT c.auth_id, c.card_id
FROM marts.fct_card_authorisations AS c
LEFT JOIN marts.dim_account AS a ON a.account_id = c.card_id AND a.product_family = 'CARD'
WHERE a.account_id IS NULL
