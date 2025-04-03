-- SQL script to check for specific column naming issues
-- Run this in the Supabase SQL Editor

-- 1. Check if accounts table has type/account_type and subtype/account_subtype
SELECT 
    'accounts type columns' as check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'type') 
        THEN 'type column exists' 
        ELSE 'type column MISSING' 
    END as type_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'account_type') 
        THEN 'account_type column exists (potential issue!)' 
        ELSE 'account_type column not found' 
    END as account_type_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'subtype') 
        THEN 'subtype column exists' 
        ELSE 'subtype column MISSING' 
    END as subtype_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'account_subtype') 
        THEN 'account_subtype column exists (potential issue!)' 
        ELSE 'account_subtype column not found' 
    END as account_subtype_status;

-- 2. Check if holdings table exists or if we're only using account_holdings table
SELECT 
    'holdings tables' as check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables 
                     WHERE table_schema = 'public' 
                     AND table_name = 'holdings') 
        THEN 'holdings table exists (potential issue!)' 
        ELSE 'holdings table not found' 
    END as holdings_table_status,
    
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables 
                     WHERE table_schema = 'public' 
                     AND table_name = 'account_holdings') 
        THEN 'account_holdings table exists' 
        ELSE 'account_holdings table MISSING' 
    END as account_holdings_table_status;

-- 3. Check security_id column format in securities table
SELECT 
    'security_id format' as check_name,
    column_name,
    data_type,
    column_default
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'securities'
    AND column_name = 'security_id';

-- 4. Check institution_id data type in relevant tables
SELECT 
    'institution_id data types' as check_name,
    table_name,
    column_name,
    data_type
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND column_name = 'institution_id'
    AND table_name IN ('accounts', 'plaid_items', 'institutions')
ORDER BY 
    table_name;

-- 5. Check for is_investment_account column in accounts table
SELECT 
    'investment account flag' as check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'is_investment_account') 
        THEN 'is_investment_account column exists' 
        ELSE 'is_investment_account column MISSING' 
    END as status;

-- 6. Check for portfolio_value column in accounts table
SELECT 
    'portfolio value' as check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'portfolio_value') 
        THEN 'portfolio_value column exists' 
        ELSE 'portfolio_value column MISSING' 
    END as status;

-- 7. Verify account_id column in accounts table 
SELECT 
    'account_id format' as check_name,
    column_name,
    data_type,
    column_default
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'accounts'
    AND column_name = 'account_id';

-- 8. Check for is_plaid_synced column in accounts table
SELECT 
    'plaid synced flag' as check_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                     WHERE table_schema = 'public' 
                     AND table_name = 'accounts' 
                     AND column_name = 'is_plaid_synced') 
        THEN 'is_plaid_synced column exists' 
        ELSE 'is_plaid_synced column MISSING' 
    END as status; 