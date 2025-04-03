-- SQL script to add missing columns to the accounts table
-- Run this in the Supabase SQL Editor

BEGIN;

-- First, check if we need to add the is_auth column
DO $$
BEGIN
    -- Add is_auth column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_auth'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_auth BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_auth column to accounts table';
    END IF;

    -- Add is_authenticated column if it doesn't exist
    -- (This is the preferred name, but code might use is_auth)
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_authenticated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_authenticated BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_authenticated column to accounts table';
    END IF;

    -- Add plaid_item_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'plaid_item_id'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN plaid_item_id UUID;
        RAISE NOTICE 'Added plaid_item_id column to accounts table';
    END IF;

    -- Add loan_type column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_type'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_type TEXT;
        RAISE NOTICE 'Added loan_type column to accounts table';
    END IF;

    -- Add loan_term column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_term'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_term TEXT;
        RAISE NOTICE 'Added loan_term column to accounts table';
    END IF;

    -- Add loan_rate column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_rate'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_rate NUMERIC;
        RAISE NOTICE 'Added loan_rate column to accounts table';
    END IF;

    -- Add is_plaid_synced column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_plaid_synced'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_plaid_synced BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_plaid_synced column to accounts table';
    END IF;

    -- Add status column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'status'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN status TEXT DEFAULT 'active';
        RAISE NOTICE 'Added status column to accounts table';
    END IF;

    -- Add last_updated column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'last_updated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN last_updated TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Added last_updated column to accounts table';
    END IF;
END $$;

-- Display the current schema for accounts table after changes
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