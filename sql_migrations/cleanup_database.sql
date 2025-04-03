-- SQL script to clean up data inconsistencies in the database
-- Run this after adding all missing columns

BEGIN;

-- Fix any NULL values in required fields
UPDATE public.accounts
SET 
    name = COALESCE(name, 'Unnamed Account'),
    current_balance = COALESCE(current_balance, 0),
    available_balance = COALESCE(available_balance, 0),
    type = COALESCE(type, 'other'),
    subtype = COALESCE(subtype, '')
WHERE
    name IS NULL OR
    current_balance IS NULL OR
    available_balance IS NULL OR
    type IS NULL OR
    subtype IS NULL;

-- Synchronize is_investment and is_investment_account flags
UPDATE public.accounts
SET is_investment = TRUE, is_investment_account = TRUE
WHERE 
    (is_investment = TRUE OR is_investment_account = TRUE) AND
    (is_investment IS DISTINCT FROM is_investment_account);

-- Synchronize is_auth and is_authenticated flags
UPDATE public.accounts
SET is_auth = COALESCE(is_authenticated, FALSE), 
    is_authenticated = COALESCE(is_auth, FALSE)
WHERE is_auth IS DISTINCT FROM is_authenticated;

-- Set Plaid flags properly
UPDATE public.accounts
SET is_plaid_synced = TRUE
WHERE account_id IS NOT NULL;

-- Set status for accounts that have NULL status
UPDATE public.accounts
SET status = 'active'
WHERE status IS NULL;

-- Fix inconsistent data types for plaid_item_id (ensure it's text)
UPDATE public.accounts
SET plaid_item_id = plaid_item_id::TEXT
WHERE plaid_item_id IS NOT NULL;

-- Remove any duplicate accounts by keeping the most recently updated one
WITH duplicates AS (
    SELECT 
        account_id,
        user_id,
        ROW_NUMBER() OVER (
            PARTITION BY account_id, user_id 
            ORDER BY last_updated DESC NULLS LAST, id DESC
        ) as row_num
    FROM 
        public.accounts
    WHERE 
        account_id IS NOT NULL
)
DELETE FROM public.accounts
WHERE id IN (
    SELECT a.id
    FROM public.accounts a
    JOIN duplicates d ON a.account_id = d.account_id AND a.user_id = d.user_id
    WHERE d.row_num > 1
);

-- Delete any demo accounts from previous test runs
-- (Optional - remove this if you want to keep demo data)
DELETE FROM public.accounts
WHERE name LIKE '%Demo%' OR name LIKE '%Test%';

-- Clean up orphaned holdings (no matching account)
DELETE FROM public.account_holdings
WHERE account_id NOT IN (SELECT id FROM public.accounts);

-- Clean up orphaned securities (no matching holdings)
DELETE FROM public.securities
WHERE id NOT IN (SELECT DISTINCT security_id FROM public.account_holdings);

-- Show updated counts of records
SELECT 'accounts' as table_name, COUNT(*) as record_count FROM public.accounts
UNION ALL
SELECT 'account_holdings' as table_name, COUNT(*) as record_count FROM public.account_holdings
UNION ALL
SELECT 'securities' as table_name, COUNT(*) as record_count FROM public.securities;

COMMIT; 