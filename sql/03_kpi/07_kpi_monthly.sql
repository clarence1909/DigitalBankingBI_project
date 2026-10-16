-- Every KPI in the catalog, one row per KPI per month (long format, for the dashboard,
-- the scorecard and the Excel pack). A check makes sure every catalog KPI appears here.
CREATE OR REPLACE TABLE kpi.kpi_monthly AS
WITH v AS (
    SELECT month_start, 'K01' AS kpi_id, CAST(applications_started AS DOUBLE) AS value FROM kpi.growth_monthly
    UNION ALL SELECT month_start, 'K02', new_customers FROM kpi.growth_monthly
    UNION ALL SELECT month_start, 'K03', onboarding_conversion FROM kpi.growth_monthly
    UNION ALL SELECT month_start, 'K04', ekyc_completion_rate FROM kpi.growth_monthly
    UNION ALL SELECT month_start, 'K05', cac FROM kpi.growth_monthly
    UNION ALL SELECT month_start, 'K06', m3_active_rate FROM kpi.growth_monthly
    UNION ALL SELECT month_start, 'K07', monthly_active_customers FROM kpi.engagement_monthly
    UNION ALL SELECT month_start, 'K08', active_customer_rate FROM kpi.engagement_monthly
    UNION ALL SELECT month_start, 'K09', txns_per_active_customer FROM kpi.engagement_monthly
    UNION ALL SELECT month_start, 'K10', card_activation_30d FROM kpi.cards_monthly
    UNION ALL SELECT month_start, 'K11', card_spend FROM kpi.cards_monthly
    UNION ALL SELECT month_start, 'K12', card_approval_rate FROM kpi.cards_monthly
    UNION ALL SELECT month_start, 'K13', total_deposits FROM kpi.deposits_monthly
    UNION ALL SELECT month_start, 'K14', casa_ratio FROM kpi.deposits_monthly
    UNION ALL SELECT month_start, 'K15', cost_of_funds FROM kpi.deposits_monthly
    UNION ALL SELECT maturity_month, 'K16', sum(retained_30d) / sum(matured_amount)
              FROM kpi.fd_maturity_outcomes WHERE window_complete GROUP BY 1
    UNION ALL SELECT month_start, 'K17', gross_loans FROM kpi.credit_monthly
    UNION ALL SELECT month_start, 'K18', amount_disbursed FROM kpi.credit_monthly
    UNION ALL SELECT month_start, 'K19', par30 FROM kpi.credit_monthly
    UNION ALL SELECT month_start, 'K20', gil_ratio FROM kpi.credit_monthly
    UNION ALL SELECT month_start, 'K21', early_delinquency_mob6 FROM kpi.credit_monthly
    UNION ALL SELECT month_start, 'K22', net_interest_income FROM kpi.finance_monthly
)
SELECT
    v.month_start,
    v.kpi_id,
    c.kpi_name,
    c.family,
    c.unit,
    c.direction,
    CAST(v.value AS DOUBLE)                                             AS value
FROM v
JOIN reference.kpi_catalog AS c ON c.kpi_id = v.kpi_id
WHERE v.value IS NOT NULL;
