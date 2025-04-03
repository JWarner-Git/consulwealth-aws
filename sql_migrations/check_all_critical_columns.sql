-- SQL script to check ALL columns in critical tables for Plaid integration
-- Run this in the Supabase SQL Editor

-- Check ALL columns in accounts table
SELECT 
    'accounts' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'accounts'
ORDER BY 
    ordinal_position;

-- Check ALL columns in securities table
SELECT 
    'securities' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'securities'
ORDER BY 
    ordinal_position;

-- Check ALL columns in account_holdings table
SELECT 
    'account_holdings' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'account_holdings'
ORDER BY 
    ordinal_position;

-- Check ALL columns in plaid_items table
SELECT 
    'plaid_items' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'plaid_items'
ORDER BY 
    ordinal_position;

-- Check ALL columns in investment_transactions table
SELECT 
    'investment_transactions' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'investment_transactions'
ORDER BY 
    ordinal_position;

-- Check ALL columns in account_investments table
SELECT 
    'account_investments' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'account_investments'
ORDER BY 
    ordinal_position;

-- Check ALL columns in institutions table
SELECT 
    'institutions' as table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'institutions'
ORDER BY 
    ordinal_position;

-- Check all foreign key relationships for these tables
SELECT 
    tc.constraint_name,
    tc.table_name as source_table,
    kcu.column_name as source_column,
    ccu.table_name as target_table,
    ccu.column_name as target_column
FROM 
    information_schema.table_constraints tc
JOIN 
    information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN 
    information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE 
    tc.constraint_type = 'FOREIGN KEY' 
    AND (tc.table_name IN (
        'accounts', 
        'securities', 
        'account_holdings', 
        'plaid_items',
        'investment_transactions',
        'account_investments',
        'institutions'
    )
    OR ccu.table_name IN (
        'accounts', 
        'securities', 
        'account_holdings', 
        'plaid_items',
        'investment_transactions',
        'account_investments',
        'institutions'
    ))
ORDER BY 
    tc.table_name, kcu.column_name;

-- Check for any inconsistencies in id/reference columns
WITH reference_columns AS (
    -- Pull out columns that might reference other tables
    SELECT
        table_name,
        column_name,
        data_type
    FROM
        information_schema.columns
    WHERE
        table_schema = 'public'
        AND (
            column_name LIKE '%\_id' ESCAPE '\' 
            OR column_name = 'id'
        )
        AND table_name IN (
            'accounts', 
            'securities', 
            'account_holdings', 
            'plaid_items',
            'investment_transactions',
            'account_investments',
            'institutions'
        )
)
SELECT
    r1.table_name,
    r1.column_name,
    r1.data_type,
    r2.table_name AS referenced_table,
    r2.column_name AS referenced_column,
    r2.data_type AS referenced_data_type,
    CASE 
        WHEN r1.data_type <> r2.data_type THEN 'Type mismatch!'
        ELSE 'OK'
    END AS status
FROM
    reference_columns r1
JOIN
    reference_columns r2
    ON (
        r1.column_name LIKE '%' || r2.table_name || '_id'
        OR (r1.column_name = 'security_id' AND r2.table_name = 'securities' AND r2.column_name = 'id')
        OR (r1.column_name = 'account_id' AND r2.table_name = 'accounts' AND r2.column_name = 'id')
        OR (r1.column_name = 'institution_id' AND r2.table_name = 'institutions' AND r2.column_name = 'id')
    )
    AND r1.table_name <> r2.table_name
ORDER BY
    r1.table_name,
    r1.column_name; 