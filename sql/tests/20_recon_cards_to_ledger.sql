-- name: recon_card_processor_to_ledger
-- severity: error
-- description: Reconciliation 2: every settled card authorisation posts to the ledger once, for the same amount, on its settlement date; and nothing posts without a settled authorisation.
-- break: UPDATE marts.fct_card_authorisations SET amount = amount + 0.01 WHERE auth_id = (SELECT min(auth_id) FROM marts.fct_card_authorisations WHERE status = 'APPROVED' AND settlement_date IS NOT NULL)
WITH processor AS (
    SELECT auth_id, amount, settlement_date
    FROM marts.fct_card_authorisations
    WHERE status = 'APPROVED' AND settlement_date IS NOT NULL
),
ledger AS (
    SELECT auth_id, -amount AS amount, posting_date
    FROM marts.fct_ledger_postings
    WHERE txn_type = 'card_purchase'
)
SELECT
    coalesce(p.auth_id, l.auth_id)                                      AS auth_id,
    p.amount                                                            AS processor_amount,
    l.amount                                                            AS ledger_amount,
    p.settlement_date,
    l.posting_date,
    CASE
        WHEN l.auth_id IS NULL THEN 'settled but not posted'
        WHEN p.auth_id IS NULL THEN 'posted without a settled authorisation'
        WHEN p.amount <> l.amount THEN 'amount differs'
        ELSE 'posted on a different date'
    END                                                                 AS issue
FROM processor AS p
FULL OUTER JOIN ledger AS l ON l.auth_id = p.auth_id
WHERE p.auth_id IS NULL OR l.auth_id IS NULL
   OR p.amount <> l.amount OR p.settlement_date <> l.posting_date
