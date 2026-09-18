-- simple example
-- SELECT *
-- FROM employees
-- WHERE age > (
--     SELECT AVG(age)
--     FROM employees
-- );

-- This works, but we can use a CTE:

WITH average_age AS (
    SELECT AVG(age) AS avg_age
    FROM employees
)
SELECT *
FROM employees
WHERE age > (
    SELECT avg_age
    FROM average_age
);

--  id | name | age | department_id 
-- ----+------+-----+---------------
--  12 | Hari |  28 |             3
--  14 | John |  30 |              
--  15 | aayu |  34 |             3
-- (3 rows)


-- 2. CTE can look like a temporary table
WITH backend_employees AS (
    SELECT *
    FROM employees
    WHERE department_id = 5
)
SELECT *
FROM backend_employees;


--  id | name | age | department_id 
-- ----+------+-----+---------------
--  11 | Ram  |  25 |             5
-- (1 row)

-- 3. CTE + JOIN    
WITH older_employees AS (
    SELECT *
    FROM employees
    WHERE age >= 25
)
SELECT
    older_employees.name AS employee,
    departments.name AS department,
    older_employees.age
FROM older_employees
JOIN departments
    ON older_employees.department_id = departments.id;

--         employee     | department | age 
-- -----------------+------------+-----
--  TransactionTest | Frontend   |  25
--  aayu            | Frontend   |  34
--  Hari            | Frontend   |  28
--  Ram             | Backend    |  25
-- (4 rows)

-- 4. Multiple CTEs

WITH older_employees AS (
    SELECT *
    FROM employees
    WHERE age >= 25
),
department_info AS (    
    SELECT *
    FROM departments
)
SELECT
    older_employees.name AS employee,
    department_info.name AS department
FROM older_employees
JOIN department_info
    ON older_employees.department_id = department_info.id;

--         employee     | department 
-- -----------------+------------
--  TransactionTest | Frontend
--  aayu            | Frontend
--  Hari            | Frontend
--  Ram             | Backend
-- (4 rows)



WITH older_employees AS (
    SELECT AVG(age) AS avg_age FROM employees
)
SELECT * FROM employees
WHERE age > (SELECT avg_age FROM older_employees);   

 
--  id | name | age | department_id 
-- ----+------+-----+---------------
--  12 | Hari |  28 |             3
--  14 | John |  30 |              
--  15 | aayu |  34 |             3
-- (3 rows)

 
-- 
-- // without cte
 SELECT
    employees.name AS employee,
    departments.name AS department
FROM employees
JOIN departments
    ON departments.id = employees.department_id
WHERE employees.department_id = 3;

-- // with cte
 WITH emp_department AS (
    SELECT * FROM employees WHERE department_id = 3
)
SELECT emp_department.name AS employee, departments.name AS department
FROM emp_department
JOIN departments ON departments.id = emp_department.department_id;   
--     employee     | department 
-- -----------------+------------
--  Hari            | Frontend
--  aayu            | Frontend
--  TransactionTest | Frontend
-- (3 rows)

-- wrong: ==> With avg_age AS (SELECT AVG(age) AS avg_age FROM employees)select employees.name AS employee from employees where age > avg_age.avg_age;

WITH avg_age AS (
    SELECT AVG(age) AS avg_age FROM employees
)
SELECT employees.name AS employee
FROM employees
WHERE age > (SELECT avg_age FROM avg_age);   

-- or
WITH avg_age AS (
    SELECT AVG(age) AS avg_age FROM employees
)
SELECT e.name AS employee
FROM employees e
CROSS JOIN avg_age
WHERE e.age > avg_age.avg_age;   

--  employee 
-- ----------
--  Hari
--  John
--  aayu
-- (3 rows)




