-- Ledger postings (transaction grain), signed: credits positive, debits negative.
CREATE OR REPLACE TABLE marts.fct_ledger_postings AS
SELECT
    p.posting_id,
    p.account_id,
    a.customer_id,
    a.product_code,
    a.product_family,
    p.posting_ts_myt,
    p.posting_date,
    CAST(date_trunc('month', p.posting_date) AS DATE)                   AS posting_month,
    p.signed_amount                                                     AS amount,
    p.direction,
    p.txn_type,
    p.is_customer_initiated,
    p.channel,
    p.reference,
    CASE WHEN p.txn_type = 'card_purchase' THEN p.reference END         AS auth_id,
    CASE WHEN p.txn_type IN ('pf_disbursement', 'pf_repayment') THEN p.reference END AS loan_id
FROM staging.stg_ledger_postings AS p
LEFT JOIN marts.dim_account AS a ON a.account_id = p.account_id;
