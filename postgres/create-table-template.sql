-- CREATE DATABASE learning_db;

-- in postgres ther is no command like USE learning_db; instead you can connect to the database using \c learning_db form terminal
-- docker exec -it postgres-db psql -U postgres



-- (random-sprint) personal@suresh-Nitro-NL16-71G:~/Desktop/learning/random-sprint$ docker exec -it postgres-db psql -U postgres


-- postgres=# \l
-- postgres=# \c learning_db
-- You are now connected to database "learning_db" as user "postgres".
-- learning_db=# 


CREATE TABLE students (
    id INTEGER,
    name VARCHAR(100),
    age INTEGER
);

drop table students;

CREATE TABLE Class (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    section VARCHAR(10),

    UNIQUE (name, section)
);

CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    age INTEGER,
    roll_no INTEGER,

    class_name VARCHAR(100),
    class_section VARCHAR(10),

    FOREIGN KEY (class_name, class_section)
        REFERENCES Class(name, section)
);

INSERT INTO students (id, name, age, roll_no)
VALUES (1, 'Suresh', 22, 1001);


CREATE TABLE employees (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 18),
    department_id INTEGER,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE CASCADE
);



CREATE TABLE employees (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 18),
    department_id INTEGER,

    FOREIGN KEY (department_id)
        REFERENCES departments(id)
        ON DELETE SET NULL
);


-- inner join example
SELECT
    employees.name AS employee_name,
    departments.name AS department_name
FROM employees
JOIN departments
    ON employees.department_id = departments.id;


    -- Left join example
SELECT
    employees.name AS employee_name,
    departments.name AS department_name
FROM employees
LEFT JOIN departments
    ON employees.department_id = departments.id;


--  employee_name | department_name 
-- ---------------+-----------------
--  Ram           | Backend
--  Hari          | Frontend
--  Sita          | AI
--  John          | 
-- (4 rows)

SELECT
    employees.name,
    employees.age,
    departments.name AS department
FROM employees
LEFT JOIN departments
    ON employees.department_id = departments.id;

    -- 
--  name | age | department 
-- ------+-----+------------
--  Ram  |  25 | Backend
--  Hari |  28 | Frontend
--  Sita |  22 | AI
--  John |  30 | 




learning_db=# SELECT *
FROM employees
JOIN departments
    ON employees.department_id = departments.id;
--  id | name | age | department_id | id |   name   
-- ----+------+-----+---------------+----+----------
--  11 | Ram  |  25 |             5 |  5 | Backend
--  12 | Hari |  28 |             3 |  3 | Frontend
--  13 | Sita |  22 |             4 |  4 | AI
-- (3 rows)

learning_db=# 
learning_db=# 
learning_db=# SELECT *
FROM employees
LEFT JOIN departments
    ON employees.department_id = departments.id;
--  id | name | age | department_id | id |   name   
-- ----+------+-----+---------------+----+----------
--  11 | Ram  |  25 |             5 |  5 | Backend
--  12 | Hari |  28 |             3 |  3 | Frontend
--  13 | Sita |  22 |             4 |  4 | AI
--  14 | John |  30 |               |    | 
-- (4 rows)

learning_db=# SELECT
    employees.name AS employee,
    departments.name AS department
FROM employees
LEFT JOIN departments
    ON employees.department_id = departments.id;
--  employee | department 
-- ----------+------------
--  Ram      | Backend
--  Hari     | Frontend
--  Sita     | AI
--  John     | 
-- (4 rows)




learning_db=# SELECT
    employees.name AS employee,
    departments.name AS department
FROM employees
FULL OUTER JOIN departments
    ON employees.department_id = departments.id;
--  employee | department 
-- ----------+------------
--  Ram      | Backend
--  Hari     | Frontend
--  Sita     | AI
--  John     | 
-- (4 rows)

