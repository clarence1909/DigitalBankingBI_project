-- name: kpi_catalog_coverage
-- severity: error
-- description: Every KPI in the catalog has values, and every scorecard KPI has a plan for the latest month.
-- break: DELETE FROM kpi.kpi_monthly WHERE kpi_id = 'K22'
SELECT c.kpi_id, c.kpi_name, 'no values in kpi_monthly' AS issue
FROM reference.kpi_catalog AS c
WHERE NOT EXISTS (SELECT 1 FROM kpi.kpi_monthly AS m WHERE m.kpi_id = c.kpi_id)
UNION ALL
SELECT c.kpi_id, c.kpi_name, 'no plan for the latest month'
FROM reference.kpi_catalog AS c
WHERE c.is_scorecard
  AND NOT EXISTS (SELECT 1 FROM reference.plan_targets AS p
                  WHERE p.kpi_id = c.kpi_id AND p.month_start = (SELECT max(month_start) FROM kpi.kpi_monthly))
