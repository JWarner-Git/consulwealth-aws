-- SQL script to fix the institution_id column type if it's incorrectly set as UUID
-- Run this in the Supabase SQL Editor

-- Check if the institution_id column exists and has the wrong type
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'plaid_items'
        AND column_name = 'institution_id'
        AND data_type = 'uuid'
    ) THEN
        -- Make a backup of existing data
        DROP TABLE IF EXISTS plaid_items_backup;
        CREATE TABLE plaid_items_backup AS SELECT * FROM plaid_items;
        
        -- Create a new institution_id column with TEXT type
        ALTER TABLE plaid_items RENAME COLUMN institution_id TO institution_id_old;
        ALTER TABLE plaid_items ADD COLUMN institution_id TEXT;
        
        -- Try to convert any valid UUIDs to text 
        UPDATE plaid_items 
        SET institution_id = institution_id_old::TEXT 
        WHERE institution_id_old IS NOT NULL;
        
        -- Drop the old column
        ALTER TABLE plaid_items DROP COLUMN institution_id_old;
        
        RAISE NOTICE 'Successfully converted institution_id column from UUID to TEXT';
    ELSE
        RAISE NOTICE 'No conversion needed for institution_id column';
    END IF;
END $$;

-- Add an index to the institution_id column for better performance
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'plaid_items' 
        AND indexname = 'idx_plaid_items_institution_id'
    ) THEN
        CREATE INDEX idx_plaid_items_institution_id ON public.plaid_items(institution_id);
        RAISE NOTICE 'Created index on institution_id column';
    END IF;
END $$;

-- Add an index on the item_id column for better performance
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'plaid_items' 
        AND indexname = 'idx_plaid_items_item_id'
    ) THEN
        CREATE INDEX idx_plaid_items_item_id ON public.plaid_items(item_id);
        RAISE NOTICE 'Created index on item_id column';
    END IF;
END $$; 