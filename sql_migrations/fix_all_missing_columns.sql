-- SQL script to add ALL possible missing columns to the accounts table
-- Run this in the Supabase SQL Editor to fix schema issues in one go

BEGIN;

-- First, check all possible column additions in a single transaction
DO $$
BEGIN
    -- Account type flags
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_investment'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_investment BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_investment column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_investment_account'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_investment_account BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_investment_account column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_credit'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_credit BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_credit column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_loan'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_loan BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_loan column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_depository'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_depository BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_depository column to accounts table';
    END IF;

    -- Authentication columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_auth'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_auth BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_auth column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_authenticated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_authenticated BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_authenticated column to accounts table';
    END IF;

    -- Plaid integration columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_plaid_synced'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_plaid_synced BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_plaid_synced column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'status'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN status TEXT DEFAULT 'active';
        RAISE NOTICE 'Added status column to accounts table';
    END IF;

    -- UI-related columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'color'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN color TEXT;
        RAISE NOTICE 'Added color column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'icon_url'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN icon_url TEXT;
        RAISE NOTICE 'Added icon_url column to accounts table';
    END IF;

    -- Loan-specific columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_type'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_type TEXT;
        RAISE NOTICE 'Added loan_type column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_term'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_term TEXT;
        RAISE NOTICE 'Added loan_term column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_rate'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_rate NUMERIC;
        RAISE NOTICE 'Added loan_rate column to accounts table';
    END IF;

    -- Other necessary columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'portfolio_value'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN portfolio_value NUMERIC;
        RAISE NOTICE 'Added portfolio_value column to accounts table';
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'last_updated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN last_updated TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Added last_updated column to accounts table';
    END IF;

    -- Handle plaid_item_id column - ensure it's TEXT type not UUID
    DECLARE
        plaid_item_id_type TEXT;
    BEGIN
        -- Check if plaid_item_id exists and what type it is
        SELECT data_type INTO plaid_item_id_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'accounts'
        AND column_name = 'plaid_item_id';
        
        IF plaid_item_id_type IS NULL THEN
            -- Column doesn't exist, create it as TEXT
            ALTER TABLE public.accounts ADD COLUMN plaid_item_id TEXT;
            RAISE NOTICE 'Added plaid_item_id column as TEXT';
        ELSIF plaid_item_id_type = 'uuid' THEN
            -- Column exists but is UUID type, convert to TEXT
            ALTER TABLE public.accounts ADD COLUMN plaid_item_id_text TEXT;
            UPDATE public.accounts SET plaid_item_id_text = plaid_item_id::TEXT;
            ALTER TABLE public.accounts DROP COLUMN plaid_item_id;
            ALTER TABLE public.accounts RENAME COLUMN plaid_item_id_text TO plaid_item_id;
            RAISE NOTICE 'Converted plaid_item_id from UUID to TEXT';
        ELSE
            RAISE NOTICE 'plaid_item_id already exists as %', plaid_item_id_type;
        END IF;
    END;
END $$;

-- Make sure investment flags are consistent
UPDATE public.accounts 
SET is_investment_account = is_investment 
WHERE is_investment_account IS DISTINCT FROM is_investment;

-- Add a separate DO block for notices
DO $$
BEGIN
    RAISE NOTICE 'Synchronized is_investment and is_investment_account flags';
END $$;

-- Make sure authentication flags are consistent
UPDATE public.accounts 
SET is_authenticated = is_auth 
WHERE is_authenticated IS DISTINCT FROM is_auth;

DO $$
BEGIN
    RAISE NOTICE 'Synchronized is_auth and is_authenticated flags';
END $$;

-- Show the current schema after all additions
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'accounts'
ORDER BY 
    ordinal_position;

COMMIT; 