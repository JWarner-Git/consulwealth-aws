-- SQL script to fix the plaid_item_id column type in the accounts table
-- Run this in the Supabase SQL Editor

BEGIN;

-- Check if plaid_item_id exists and what its current type is
DO $$
DECLARE
    current_type TEXT;
BEGIN
    -- Get the current data type of plaid_item_id column, if it exists
    SELECT data_type INTO current_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'accounts'
    AND column_name = 'plaid_item_id';
    
    -- If the column exists
    IF current_type IS NOT NULL THEN
        RAISE NOTICE 'plaid_item_id column exists with type: %', current_type;
        
        -- If it's currently UUID type, change it to TEXT
        IF current_type = 'uuid' THEN
            -- First temporarily create a new column to preserve values
            ALTER TABLE public.accounts ADD COLUMN plaid_item_id_text TEXT;
            
            -- Convert existing UUIDs to text
            UPDATE public.accounts SET plaid_item_id_text = plaid_item_id::TEXT;
            
            -- Drop the UUID column
            ALTER TABLE public.accounts DROP COLUMN plaid_item_id;
            
            -- Rename the text column back to plaid_item_id
            ALTER TABLE public.accounts RENAME COLUMN plaid_item_id_text TO plaid_item_id;
            
            RAISE NOTICE 'Changed plaid_item_id from UUID to TEXT';
        ELSE
            RAISE NOTICE 'plaid_item_id is already type %, no change needed', current_type;
        END IF;
    ELSE
        -- If the column doesn't exist, create it with TEXT type
        ALTER TABLE public.accounts ADD COLUMN plaid_item_id TEXT;
        RAISE NOTICE 'Added plaid_item_id column with TEXT type';
    END IF;
END $$;

-- Also add is_auth and is_authenticated columns if not present
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
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_authenticated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_authenticated BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_authenticated column to accounts table';
    END IF;
END $$;

-- Display the current schema for plaid_item_id column
SELECT 
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public'
    AND table_name = 'accounts'
    AND column_name = 'plaid_item_id';

COMMIT; 