-- The monthly scorecard: six KPIs against plan with a red, amber or green status.
-- Status rules (direction-aware):
--   higher is better: green at or above plan; amber within the tolerance below plan; else red
--   lower is better:  green at or below plan; amber within the tolerance above plan; else red
-- The label and arrow carry the same meaning as the colour, so status never relies on colour alone.
CREATE OR REPLACE TABLE kpi.scorecard AS
WITH k AS (
    SELECT
        m.month_start,
        m.kpi_id,
        m.value                                                         AS actual,
        lag(m.value) OVER (PARTITION BY m.kpi_id ORDER BY m.month_start) AS prior_month
    FROM kpi.kpi_monthly AS m
    JOIN reference.kpi_catalog AS c ON c.kpi_id = m.kpi_id
    WHERE c.is_scorecard
),
rated AS (
    SELECT
        k.*,
        c.kpi_name,
        c.unit,
        c.direction,
        c.owner,
        c.amber_tolerance,
        p.plan_value                                                    AS plan,
        CASE
            WHEN p.plan_value IS NULL THEN NULL
            WHEN c.direction = 'higher' THEN
                CASE WHEN k.actual >= p.plan_value THEN 'GREEN'
                     WHEN k.actual >= p.plan_value * (1 - c.amber_tolerance) THEN 'AMBER'
                     ELSE 'RED' END
            ELSE
                CASE WHEN k.actual <= p.plan_value THEN 'GREEN'
                     WHEN k.actual <= p.plan_value * (1 + c.amber_tolerance) THEN 'AMBER'
                     ELSE 'RED' END
        END                                                             AS status
    FROM k
    JOIN reference.kpi_catalog AS c ON c.kpi_id = k.kpi_id
    LEFT JOIN reference.plan_targets AS p ON p.kpi_id = k.kpi_id AND p.month_start = k.month_start
)
SELECT
    month_start,
    kpi_id,
    kpi_name,
    unit,
    direction,
    owner,
    actual,
    prior_month,
    plan,
    actual / nullif(plan, 0)                                            AS pct_of_plan,
    actual - plan                                                       AS variance_to_plan,
    amber_tolerance,
    status,
    CASE status WHEN 'GREEN' THEN 'On plan' WHEN 'AMBER' THEN 'Watch' WHEN 'RED' THEN 'Off plan' END AS status_label,
    CASE status WHEN 'GREEN' THEN 1 WHEN 'AMBER' THEN 2 WHEN 'RED' THEN 3 END AS status_rank,
    CASE
        WHEN prior_month IS NULL OR abs(actual - prior_month) <= abs(prior_month) * 0.001 THEN 'flat'
        WHEN (actual > prior_month) = (direction = 'higher') THEN 'better'
        ELSE 'worse'
    END                                                                 AS change_vs_prior_month
FROM rated;
