-- name: ratio_kpis_between_0_and_1
-- severity: error
-- description: Every KPI measured as a share lies between 0% and 100%.
-- break: UPDATE kpi.kpi_monthly SET value = 1.5 WHERE kpi_id = 'K14' AND month_start = DATE '2026-08-01'
SELECT month_start, kpi_id, kpi_name, value
FROM kpi.kpi_monthly
WHERE unit = 'pct' AND (value < 0 OR value > 1)
