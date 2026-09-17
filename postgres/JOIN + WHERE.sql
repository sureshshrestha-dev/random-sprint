SELECT
    employees.name AS employee,
    departments.name AS department
FROM employees
JOIN departments
    ON employees.department_id = departments.id
WHERE departments.name = 'Backend';


-- Find employees older than 25
SELECT
    employees.name AS employee,
    employees.age,
    departments.name AS department
FROM employees
JOIN departments
    ON employees.department_id = departments.id
WHERE employees.age > 25;


-- JOIN + WHERE + ORDER BY

SELECT
    employees.name AS employee,
    employees.age,
    departments.name AS department
FROM employees
JOIN departments
    ON employees.department_id = departments.id
WHERE employees.age >= 22
ORDER BY employees.age DESC;




SELECT employees.name AS employee, employees.age,departments.name AS department FROM employees JOIN departments ON employees.department_id = departments.id WHERE employees.age >= 22 ORDER BY departments.name DESC LIMIT 2;




-- Next Lesson: Aggregate Functions
-- COUNT() → how many
-- SUM()   → total
-- AVG()   → average
-- MIN()   → smallest
-- MAX()   → largest

SELECT COUNT(*) FROM employees;
--  count 
-- -------
--      4
-- (1 row)


SELECT COUNT(*) FROM employees WHERE age >= 25;
--  count 
-- -------
--      3
-- (1 row)

SELECT AVG(age) FROM employees;
--          avg         
-- ---------------------
--  26.2500000000000000
-- (1 row)

SELECT
    MIN(age) AS youngest,
    MAX(age) AS oldest
FROM employees;

--  youngest | oldest 
-- ----------+--------
--        22 |     30
-- (1 row)


-- 5. Multiple aggregates together

SELECT
    COUNT(*) AS total_employees,
    AVG(age) AS average_age,
    MIN(age) AS youngest,
    MAX(age) AS oldest
FROM employees;

--  total_employees |     average_age     | youngest | oldest 
-- -----------------+---------------------+----------+--------
--                4 | 26.2500000000000000 |       22 |     30
-- (1 row)

-- Now the important part: GROUP BY
-- How many employees does each department have?
SELECT
    departments.name AS department,
    COUNT(employees.id) AS employee_count
FROM departments
LEFT JOIN employees
    ON employees.department_id = departments.id
GROUP BY departments.name;

-- department | employee_count 
-- ------------+----------------
--  Backend    |              1
--  Frontend   |              2
--  AI         |              1
-- (3 rows)


-- One important thing: COUNT(*) vs COUNT(column)


SELECT
    departments.name AS department,
    COUNT(employees.id) AS employee_count
FROM departments
LEFT JOIN employees
    ON employees.department_id = departments.id
GROUP BY departments.name
HAVING COUNT(employees.id) >= 2;