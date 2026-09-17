-- docker run --name postgres-db \
--   -e POSTGRES_USER=postgres \
--   -e POSTGRES_PASSWORD=postgres \
--   -e POSTGRES_DB=mydatabase \
--   -p 5432:5432 \
--   -d postgres:16


-- 6. Useful PostgreSQL commands
-- These commands are psql commands, not SQL.
-- List databases:

\l

-- Connect to a database:

\c my_database


-- cretae student table
Create table students (
    id INTEGER,
    name VARCHAR(100),
    age INTEGER,
    roll_no INTEGER,
    PRIMARY KEY (id)
);


-- List tables:
\dt


-- Describe a table:
\d students

-- Show help:
\?

-- Quit:
\q

-- Notice the \.

-- For example:

\dt

-- is a PostgreSQL psql command.

-- While:

SELECT * FROM students;

-- is SQL.

-- That's an important distinction.