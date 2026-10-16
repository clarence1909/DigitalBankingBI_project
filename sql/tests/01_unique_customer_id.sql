-- name: unique_customer_id
-- severity: error
-- description: Each customer appears once in dim_customer.
-- break: INSERT INTO marts.dim_customer SELECT * FROM marts.dim_customer LIMIT 1
SELECT customer_id, count(*) AS copies
FROM marts.dim_customer
GROUP BY customer_id
HAVING count(*) > 1
