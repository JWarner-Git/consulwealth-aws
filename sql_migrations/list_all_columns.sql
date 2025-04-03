-- Simple script to list ALL columns from critical tables
-- Run this in the Supabase SQL Editor

-- First, list all our critical tables in a CTE
WITH critical_tables AS (
    SELECT 'accounts' AS table_name UNION ALL
    SELECT 'securities' UNION ALL
    SELECT 'account_holdings' UNION ALL
    SELECT 'plaid_items' UNION ALL
    SELECT 'institutions' UNION ALL
    SELECT 'investment_transactions' UNION ALL
    SELECT 'account_investments' UNION ALL
    SELECT 'account_credit_details' UNION ALL
    SELECT 'account_loan_details' UNION ALL
    SELECT 'profiles' UNION ALL
    SELECT 'transactions'
)

-- Simply select all columns from information_schema
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default
FROM
    information_schema.columns c
JOIN
    critical_tables t ON c.table_name = t.table_name
WHERE
    c.table_schema = 'public'
ORDER BY
    c.table_name,
    c.ordinal_position; 