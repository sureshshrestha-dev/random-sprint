-- Lesson: Subqueries
-- SELECT AVG(age) FROM employees;

-- SELECT * FROM employees WHERE age > 27.8;

SELECT *
FROM employees
WHERE age > (
    SELECT AVG(age)
    FROM employees
);


--  id | name | age | department_id 
-- ----+------+-----+---------------
--  12 | Hari |  28 |             3
--  14 | John |  30 |              
--  15 | aayu |  34 |             3
-- (3 rows)

-- 2. Subquery with IN
-- Suppose we want employees who belong to departments named Backend or Frontend.
-- SELECT id FROM departments WHERE name IN ('Backend', 'Frontend');
--  id 
-- ----
--   3
--   5
-- (2 rows) then

-- SELECT * FROM employees WHERE department_id IN (5, 3);

-- intsead
SELECT *
FROM employees
WHERE department_id IN (
    SELECT id
    FROM departments
    WHERE name IN ('Backend', 'Frontend')
);
--  id | name | age | department_id 
-- ----+------+-----+---------------
--  11 | Ram  |  25 |             5
--  12 | Hari |  28 |             3
--  15 | aayu |  34 |             3
-- (3 rows)


-- 3. Subquery vs JOIN
-- The same thing can often be written using a JOIN:
SELECT
    employees.name AS employee,
    departments.name AS department
FROM employees
JOIN departments
    ON employees.department_id = departments.id
WHERE departments.name IN ('Backend', 'Frontend');

--  employee | department 
-- ----------+------------
--  Ram      | Backend
--  Hari     | Frontend
--  aayu     | Frontend
-- (3 rows)

-- 4. Scalar subquery

SELECT * FROM employees
WHERE age > (
    SELECT AVG(age)
    FROM employees
);   

SELECT *
FROM employees
WHERE department_id IN (
    SELECT id
    FROM departments
    WHERE name = 'Backend'
);


-- Next Lesson: Indexes
CREATE INDEX idx_employees_name
ON employees(name);

CREATE INDEX idx_employees_department_id
ON employees(department_id);
-- check index
\d employees


EXPLAIN
SELECT *
FROM employees
WHERE name = 'Ram';
--                         QUERY PLAN                         
-- -----------------------------------------------------------
--  Seq Scan on employees  (cost=0.00..1.06 rows=1 width=230)
--    Filter: ((name)::text = 'Ram'::text)
-- (2 rows)

EXPLAIN ANALYZE
SELECT *
FROM employees
WHERE name = 'Ram';
--                                              QUERY PLAN                                              
-- -----------------------------------------------------------------------------------------------------
--  Seq Scan on employees  (cost=0.00..1.06 rows=1 width=230) (actual time=0.016..0.019 rows=1 loops=1)
--    Filter: ((name)::text = 'Ram'::text)
--    Rows Removed by Filter: 4
--  Planning Time: 0.102 ms
--  Execution Time: 0.037 ms
-- (5 rows)

SET enable_seqscan = OFF;
-- SET // disable sequential scan, so that the query planner will use the index instead of scanning the entire table

EXPLAIN
SELECT *
FROM employees
WHERE name = 'Ram';
--                                QUERY PLAN                               
-- ------------------------------------------------------------------------
--  Index Scan using name on employees  (cost=0.13..8.15 rows=1 width=230)
--    Index Cond: ((name)::text = 'Ram'::text)
-- (2 rows)
-- SET enable_seqscan = ON;
-- SET // enable sequential scan, so that the query planner will use the sequential scan instead of the index


-- Important: don't disable sequential scans in a real application just to force indexes. We're only doing it here so you can see how the index appears in an execution plan.


-- Next Lesson: Transactions


-- BEGIN
--   ↓
-- Make changes
--   ↓
-- Something goes wrong?
--   ↓
-- ROLLBACK
--   ↓
-- Changes undone

-- Or:

-- BEGIN
--   ↓
-- Make changes
--   ↓
-- Everything successful
--   ↓
-- COMMIT
--   ↓
Changes saved

-- //////////////
-- learning_db=# SELECT * FROM employees;
--  id | name | age | department_id 
-- ----+------+-----+---------------
--  11 | Ram  |  25 |             5
--  12 | Hari |  28 |             3
--  13 | Sita |  22 |             4
--  14 | John |  30 |              
--  15 | aayu |  34 |             3
-- (5 rows)

-- learning_db=# BEGIN;

-- INSERT INTO employees (name, age, department_id)
-- VALUES ('TransactionTest', 25, 3);

-- SELECT * FROM employees;
-- BEGIN
-- INSERT 0 1x
--  id |      name       | age | department_id 
-- ----+-----------------+-----+---------------
--  11 | Ram             |  25 |             5
--  12 | Hari            |  28 |             3
--  13 | Sita            |  22 |             4
--  14 | John            |  30 |              
--  15 | aayu            |  34 |             3
--  16 | TransactionTest |  25 |             3
-- (6 rows)

-- learning_db=*# ROLLBACK;
-- ROLLBACK
-- learning_db=# ROLLBACK;SELECT * FROM employees;
-- WARNING:  there is no transaction in progress
-- ROLLBACK
--  id | name | age | department_id 
-- ----+------+-----+---------------
--  11 | Ram  |  25 |             5
--  12 | Hari |  28 |             3
--  13 | Sita |  22 |             4
--  14 | John |  30 |              
--  15 | aayu |  34 |             3
-- (5 rows)


-- 
-- 
-- Next Lesson: ACID Transactions
-- ACID stands for ADDING, CONSISTENCY, ISOLATION, DURABILITY. It is a set of properties that guarantee that database transactions are processed reliably.
-- 1. Atomicity
-- "All or nothing."

-- 2. Consistency
-- The database should remain valid according to its rules.

-- 3. Isolation
-- Imagine two requests are modifying the database at approximately the same time.

-- 4. Durability
-- Once you COMMIT the database treats those changes as committed data and works to preserve them even if the database process/server subsequently restarts.