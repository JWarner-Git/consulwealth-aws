-- SQL script to remove all demo data from the database
-- Run this in the Supabase SQL Editor

-- Start a transaction to ensure all operations complete or none do
BEGIN;

-- 1. First, check if we need to add the icon_url and color columns
DO $$
BEGIN
    -- Add icon_url column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'icon_url'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN icon_url TEXT;
        RAISE NOTICE 'Added icon_url column to accounts table';
    END IF;

    -- Add color column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'color'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN color TEXT;
        RAISE NOTICE 'Added color column to accounts table';
    END IF;
END $$;

-- 2. Create a temporary table to track changes
CREATE TEMP TABLE delete_stats (
    table_name TEXT,
    records_deleted INTEGER
);

-- 3. Delete all demo securities (unrealistic ticker symbols)
WITH deleted_securities AS (
    DELETE FROM securities 
    WHERE 
        name LIKE 'Demo%'
        OR name LIKE 'Plaid%' 
        OR ticker_symbol LIKE 'PLAID%'
        OR security_id IN (
            SELECT security_id 
            FROM securities 
            WHERE security_id LIKE 'demo-%'
            OR security_id LIKE 'plaid-%'
        )
    RETURNING id
)
INSERT INTO delete_stats (table_name, records_deleted)
VALUES ('securities', (SELECT COUNT(*) FROM deleted_securities));

-- 4. Delete account holdings related to demo accounts
WITH deleted_holdings AS (
    DELETE FROM account_holdings
    WHERE 
        account_id IN (
            SELECT id FROM accounts 
            WHERE 
                name LIKE 'Demo%' 
                OR name LIKE 'Plaid%'
                OR account_id LIKE 'demo-%'
                OR account_id LIKE 'plaid-%'
        )
    RETURNING id
)
INSERT INTO delete_stats (table_name, records_deleted)
VALUES ('account_holdings', (SELECT COUNT(*) FROM deleted_holdings));

-- 5. Delete all demo accounts
WITH deleted_accounts AS (
    DELETE FROM accounts 
    WHERE 
        name LIKE 'Demo%' 
        OR name LIKE 'Plaid%'
        OR account_id LIKE 'demo-%'
        OR account_id LIKE 'plaid-%'
    RETURNING id
)
INSERT INTO delete_stats (table_name, records_deleted)
VALUES ('accounts', (SELECT COUNT(*) FROM deleted_accounts));

-- 6. Reset any unrealistic portfolio values
WITH updated_accounts AS (
    UPDATE accounts
    SET portfolio_value = NULL
    WHERE portfolio_value > 10000000 -- $10 million is likely demo data
    RETURNING id
)
INSERT INTO delete_stats (table_name, records_deleted)
VALUES ('accounts_reset', (SELECT COUNT(*) FROM updated_accounts));

-- 7. Show the deletion summary
SELECT * FROM delete_stats;

-- 8. Verify that no demo data remains
SELECT 'Demo securities remaining' as check, COUNT(*) as count
FROM securities 
WHERE 
    name LIKE 'Demo%'
    OR name LIKE 'Plaid%' 
    OR ticker_symbol LIKE 'PLAID%'
    OR security_id LIKE 'demo-%'
    OR security_id LIKE 'plaid-%'
UNION ALL
SELECT 'Demo accounts remaining' as check, COUNT(*) as count
FROM accounts 
WHERE 
    name LIKE 'Demo%' 
    OR name LIKE 'Plaid%'
    OR account_id LIKE 'demo-%'
    OR account_id LIKE 'plaid-%';

-- Commit all changes
COMMIT; 