-- SQL script to export database schema to a temporary table
-- Run this in the Supabase SQL Editor

-- Create a temporary table to store the schema information
CREATE TEMP TABLE schema_export AS
SELECT
    t.table_name,
    c.column_name,
    c.data_type,
    c.column_default,
    c.is_nullable,
    c.character_maximum_length,
    pg_catalog.col_description(format('%s.%s', c.table_schema, c.table_name)::regclass::oid, c.ordinal_position) as column_description,
    c.ordinal_position
FROM
    information_schema.tables t
JOIN
    information_schema.columns c ON t.table_name = c.table_name AND t.table_schema = c.table_schema
WHERE
    t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
ORDER BY
    t.table_name,
    c.ordinal_position;

-- Display the schema export
SELECT * FROM schema_export ORDER BY table_name, ordinal_position;

-- Count tables and columns
SELECT 'Number of tables:' as stat, COUNT(DISTINCT table_name)::text as value FROM schema_export
UNION ALL
SELECT 'Total columns:' as stat, COUNT(*)::text as value FROM schema_export;

-- Display table summary (table name and column count)
SELECT 
    table_name, 
    COUNT(*) as column_count
FROM 
    schema_export
GROUP BY 
    table_name
ORDER BY 
    table_name;

-- You can export this data to CSV by clicking 'Download' in the Supabase SQL Editor
-- after running this query 