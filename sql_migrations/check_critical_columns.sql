-- SQL script to check critical columns for Plaid investment integration
-- Run this in the Supabase SQL Editor

-- Check accounts table columns (focus on type/account_type and subtype/account_subtype)
SELECT 
    'accounts' as table_name,
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'accounts'
    AND column_name IN ('id', 'user_id', 'institution_id', 'account_id', 'name', 
                        'type', 'account_type', 'subtype', 'account_subtype',
                        'is_investment_account', 'portfolio_value', 'current_balance',
                        'available_balance', 'is_plaid_synced', 'mask')
ORDER BY 
    ordinal_position;

-- Check securities table columns
SELECT 
    'securities' as table_name,
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'securities'
    AND column_name IN ('id', 'security_id', 'name', 'ticker_symbol', 
                        'isin', 'cusip', 'type', 'close_price',
                        'close_price_as_of', 'currency_code')
ORDER BY 
    ordinal_position;

-- Check account_holdings table columns (check if table is named correctly)
SELECT 
    'account_holdings' as table_name,
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'account_holdings'
    AND column_name IN ('id', 'account_id', 'security_id', 'cost_basis', 
                        'quantity', 'institution_value', 'institution_price',
                        'institution_price_as_of')
ORDER BY 
    ordinal_position;

-- Check if 'holdings' table exists (old name) and its columns
SELECT 
    'holdings' as table_name,
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'holdings'
ORDER BY 
    ordinal_position;

-- Check plaid_items table columns
SELECT 
    'plaid_items' as table_name,
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'plaid_items'
    AND column_name IN ('id', 'user_id', 'item_id', 'access_token', 
                        'institution_id', 'connection_status', 'update_type',
                        'last_successful_update', 'next_hard_refresh')
ORDER BY 
    ordinal_position;

-- Check institution_id data type in accounts and plaid_items tables
SELECT 
    'Institution ID Data Types' as check_name,
    a.table_name,
    a.column_name,
    a.data_type
FROM 
    information_schema.columns a
WHERE 
    a.table_schema = 'public' 
    AND a.column_name = 'institution_id'
    AND a.table_name IN ('accounts', 'plaid_items')
ORDER BY 
    a.table_name;

-- Check for any foreign key constraints between critical tables
SELECT 
    'Foreign Keys' as check_name,
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
    AND (tc.table_name IN ('accounts', 'securities', 'account_holdings', 'plaid_items')
    OR ccu.table_name IN ('accounts', 'securities', 'account_holdings', 'plaid_items'))
ORDER BY 
    tc.table_name, kcu.column_name; 