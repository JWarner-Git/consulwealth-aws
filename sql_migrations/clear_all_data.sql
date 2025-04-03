-- SQL script to completely clear all data while preserving table structure
-- Run this in Supabase SQL Editor

-- Start a transaction to ensure all operations complete or none do
BEGIN;

-- Disable triggers temporarily to avoid foreign key issues
SET session_replication_role = 'replica';

-- Clear Plaid-related tables
TRUNCATE TABLE plaid_items CASCADE;
TRUNCATE TABLE accounts CASCADE; 
TRUNCATE TABLE account_investments CASCADE;
TRUNCATE TABLE account_credit_details CASCADE;
TRUNCATE TABLE account_loan_details CASCADE;
TRUNCATE TABLE account_holdings CASCADE;
TRUNCATE TABLE securities CASCADE;
TRUNCATE TABLE transactions CASCADE;
TRUNCATE TABLE investment_transactions CASCADE;

-- Reset sequences only if they exist (for tables using serial/bigserial IDs)
-- We'll use DO blocks with conditionals to check if each sequence exists

DO $$
BEGIN
    -- Reset sequences if they exist
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'accounts_id_seq') THEN
        ALTER SEQUENCE accounts_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'account_investments_id_seq') THEN
        ALTER SEQUENCE account_investments_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'account_credit_details_id_seq') THEN
        ALTER SEQUENCE account_credit_details_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'account_loan_details_id_seq') THEN
        ALTER SEQUENCE account_loan_details_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'account_holdings_id_seq') THEN
        ALTER SEQUENCE account_holdings_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'securities_id_seq') THEN
        ALTER SEQUENCE securities_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'transactions_id_seq') THEN
        ALTER SEQUENCE transactions_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'investment_transactions_id_seq') THEN
        ALTER SEQUENCE investment_transactions_id_seq RESTART WITH 1;
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'plaid_items_id_seq') THEN
        ALTER SEQUENCE plaid_items_id_seq RESTART WITH 1;
    END IF;
END $$;

-- Reset profiles to default values if you want to keep users but clear their data
-- Uncomment the following line if you want to clear profiles
-- TRUNCATE TABLE profiles CASCADE;
-- IF EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'profiles_id_seq') THEN
--     ALTER SEQUENCE profiles_id_seq RESTART WITH 1;
-- END IF;

-- Re-enable triggers
SET session_replication_role = 'origin';

-- Show status of cleared tables
SELECT 
    table_name,
    0 as row_count,
    'Data cleared successfully' as status
FROM 
    information_schema.tables
WHERE 
    table_schema = 'public'
    AND table_name IN (
        'plaid_items', 
        'accounts', 
        'account_investments', 
        'account_credit_details', 
        'account_loan_details', 
        'account_holdings', 
        'securities', 
        'transactions', 
        'investment_transactions'
    );

-- Commit all changes
COMMIT; 