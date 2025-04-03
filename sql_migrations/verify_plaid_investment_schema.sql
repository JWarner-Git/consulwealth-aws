-- SQL script to verify that all required schema elements are in place
-- for the Plaid investment integration.
-- Run this in the Supabase SQL Editor

-- Check if all required columns exist and report any issues
SELECT 'Verifying schema for Plaid investment integration...';

-- Create a temporary table to store verification results
CREATE TEMP TABLE schema_checks (
    check_name TEXT,
    status TEXT,
    issue TEXT,
    fix TEXT
);

-- Check accounts table columns
DO $$
DECLARE
    missing_columns TEXT[];
    column_exists BOOLEAN;
BEGIN
    missing_columns := '{}';
    
    -- Check each required column
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'type'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'type');
    END IF;
    
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'subtype'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'subtype');
    END IF;
    
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_investment_account'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'is_investment_account');
    END IF;
    
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_investment'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'is_investment');
    END IF;
    
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'portfolio_value'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'portfolio_value');
    END IF;
    
    -- Report results
    IF array_length(missing_columns, 1) IS NULL THEN
        INSERT INTO schema_checks (check_name, status, issue, fix)
        VALUES ('Accounts Table', 'PASSED', NULL, NULL);
    ELSE
        INSERT INTO schema_checks (check_name, status, issue, fix)
        VALUES (
            'Accounts Table', 
            'FAILED', 
            'Missing columns: ' || array_to_string(missing_columns, ', '),
            'Add missing columns to the accounts table'
        );
    END IF;
END $$;

-- Check securities table
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'securities'
    ) INTO table_exists;
    
    IF table_exists THEN
        INSERT INTO schema_checks (check_name, status, issue, fix)
        VALUES ('Securities Table', 'PASSED', NULL, NULL);
    ELSE
        INSERT INTO schema_checks (check_name, status, issue, fix)
        VALUES (
            'Securities Table',
            'FAILED',
            'The securities table does not exist',
            'Run the appropriate migration to create the securities table'
        );
    END IF;
END $$;

-- Check account_holdings table
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'account_holdings'
    ) INTO table_exists;
    
    IF table_exists THEN
        INSERT INTO schema_checks (check_name, status, issue, fix)
        VALUES ('Account Holdings Table', 'PASSED', NULL, NULL);
    ELSE
        INSERT INTO schema_checks (check_name, status, issue, fix)
        VALUES (
            'Account Holdings Table',
            'FAILED',
            'The account_holdings table does not exist',
            'Run the appropriate migration to create the account_holdings table'
        );
    END IF;
END $$;

-- Check for accounts with inconsistent investment flags
INSERT INTO schema_checks (check_name, status, issue, fix)
SELECT 
    'Investment Account Flags', 
    CASE WHEN count(*) = 0 THEN 'PASSED' ELSE 'WARNING' END,
    CASE WHEN count(*) = 0 THEN NULL ELSE 'Found ' || count(*) || ' accounts with inconsistent investment flags' END,
    CASE WHEN count(*) = 0 THEN NULL ELSE 'Run UPDATE accounts SET is_investment_account = is_investment WHERE is_investment_account != is_investment' END
FROM 
    accounts 
WHERE 
    is_investment_account IS DISTINCT FROM is_investment;

-- Check for duplicate accounts (same user_id and account_id)
INSERT INTO schema_checks (check_name, status, issue, fix)
SELECT 
    'Duplicate Accounts', 
    CASE WHEN count(*) = 0 THEN 'PASSED' ELSE 'WARNING' END,
    CASE WHEN count(*) = 0 THEN NULL ELSE 'Found ' || count(*) || ' duplicate accounts (same user_id and account_id)' END,
    CASE WHEN count(*) = 0 THEN NULL ELSE 'Manually review and resolve duplicate accounts' END
FROM (
    SELECT user_id, account_id, COUNT(*) as count
    FROM accounts
    GROUP BY user_id, account_id
    HAVING COUNT(*) > 1
) as dupes;

-- Display the verification results
SELECT * FROM schema_checks;

-- Show all required columns for the accounts table
SELECT 
    'accounts' as table_name,
    column_name,
    data_type,
    CASE 
        WHEN column_name IN ('is_investment', 'is_investment_account', 'is_credit', 'is_loan', 'is_depository') THEN 'Boolean flag for account type'
        WHEN column_name = 'portfolio_value' THEN 'Total value of investment holdings'
        WHEN column_name = 'type' THEN 'Account type from Plaid (investment, depository, etc.)'
        WHEN column_name = 'subtype' THEN 'Account subtype from Plaid (401k, checking, etc.)'
        WHEN column_name = 'current_balance' THEN 'Current balance of the account'
        WHEN column_name = 'available_balance' THEN 'Available balance of the account'
        ELSE NULL
    END as description
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public' 
    AND table_name = 'accounts'
    AND column_name IN (
        'type', 'subtype', 'is_investment', 'is_investment_account',
        'is_credit', 'is_loan', 'is_depository', 'portfolio_value',
        'current_balance', 'available_balance'
    )
ORDER BY 
    column_name;

-- Display schema for account_holdings table
SELECT 
    'account_holdings' as table_name, 
    column_name, 
    data_type 
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public' 
    AND table_name = 'account_holdings'
ORDER BY 
    ordinal_position;

-- Display schema for securities table
SELECT 
    'securities' as table_name, 
    column_name, 
    data_type 
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public' 
    AND table_name = 'securities'
ORDER BY 
    ordinal_position; 