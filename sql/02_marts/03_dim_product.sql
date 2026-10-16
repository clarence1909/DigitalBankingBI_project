-- Products: savings (CASA), fixed deposits, the debit card and personal financing.
CREATE OR REPLACE TABLE marts.dim_product AS
SELECT
    product_code,
    product_name,
    product_family,
    TRY_CAST(nullif(tenor_months, '') AS INTEGER)      AS tenor_months,
    is_deposit
FROM reference.products;
