-- Accounts: savings, fixed deposits and debit cards, with their product and terms.
CREATE OR REPLACE TABLE marts.dim_account AS
SELECT
    a.account_id,
    a.customer_id,
    a.product_code,
    p.product_name,
    a.product_family,
    a.open_date,
    a.close_date,
    a.account_status,
    CASE WHEN a.product_family = 'FD' THEN a.interest_rate_pct END     AS fd_rate_pct,
    a.fd_principal,
    a.tenor_months,
    a.maturity_date,
    a.campaign_code,
    coalesce(a.campaign_code = 'RAYA25', false)                         AS is_promo_fd,
    a.rollover_of_account_id,
    a.linked_account_id,
    a.card_activation_date
FROM staging.stg_accounts AS a
LEFT JOIN marts.dim_product AS p ON p.product_code = a.product_code;
