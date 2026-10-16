-- Question (Head of Cards, Q16): What did customers spend on with the debit card from June to
-- August 2026, and how big is a typical purchase in each category?
SELECT
    merchant_category,
    category_group,
    count(*)                                                            AS purchases,
    round(sum(amount), 2)                                               AS spend,
    round(sum(amount) * 100.0 / sum(sum(amount)) OVER (), 1)            AS pct_of_spend,
    round(median(amount), 2)                                            AS median_purchase
FROM marts.fct_card_authorisations
WHERE is_approved_final
  AND auth_month BETWEEN DATE '2026-06-01' AND DATE '2026-08-01'
GROUP BY 1, 2
ORDER BY spend DESC
