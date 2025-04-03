-- SQL script to fix accounts table schema
-- Run this in the Supabase SQL Editor

-- First check if the 'accounts' table exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
    ) THEN
        RAISE EXCEPTION 'The accounts table does not exist in the database';
    END IF;
END $$;

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Add is_plaid_synced if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_plaid_synced'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_plaid_synced BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added is_plaid_synced column';
    END IF;

    -- Add status column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'status'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN status TEXT DEFAULT 'active';
        RAISE NOTICE 'Added status column';
    END IF;

    -- Add is_credit if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_credit'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_credit BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added is_credit column';
    END IF;

    -- Add is_loan if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_loan'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_loan BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added is_loan column';
    END IF;

    -- Add is_depository if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_depository'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_depository BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added is_depository column';
    END IF;

    -- Add icon_url if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'icon_url'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN icon_url TEXT;
        RAISE NOTICE 'Added icon_url column';
    END IF;

    -- Add color if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'color'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN color TEXT;
        RAISE NOTICE 'Added color column';
    END IF;

    -- Add loan_type if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_type'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_type TEXT;
        RAISE NOTICE 'Added loan_type column';
    END IF;

    -- Add loan_term if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_term'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_term INTEGER;
        RAISE NOTICE 'Added loan_term column';
    END IF;

    -- Add loan_rate if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_rate'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_rate NUMERIC;
        RAISE NOTICE 'Added loan_rate column';
    END IF;

    -- Make sure the is_authenticated column exists (mapped from is_auth)
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_authenticated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_authenticated BOOLEAN DEFAULT false;
        RAISE NOTICE 'Added is_authenticated column';
    END IF;
END $$;

-- Now verify the columns we've added
SELECT 
    column_name, 
    data_type 
FROM 
    information_schema.columns 
WHERE 
    table_schema = 'public' 
    AND table_name = 'accounts'
ORDER BY 
    ordinal_position; 