-- SQL script to fix the foreign key constraint on institution_id
-- Run this in the Supabase SQL Editor

-- First, identify the constraint name
DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'public.accounts'::regclass
    AND conname LIKE '%institution_id%';
    
    IF constraint_name IS NOT NULL THEN
        -- Drop the existing foreign key constraint
        EXECUTE 'ALTER TABLE public.accounts DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped foreign key constraint: %', constraint_name;
    END IF;
END $$;

-- Now we can safely change the column type
DO $$
BEGIN
    -- Change institution_id to TEXT type
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'institution_id'
        AND data_type <> 'text'
    ) THEN
        ALTER TABLE public.accounts 
        ALTER COLUMN institution_id TYPE TEXT USING institution_id::TEXT;
        RAISE NOTICE 'Changed institution_id column type to TEXT';
    END IF;
END $$;

-- Check if there's an institutions table with TEXT id
DO $$
DECLARE
    has_text_id boolean := FALSE;
    institutions_exist boolean := FALSE;
BEGIN
    -- Check if institutions table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'institutions'
    ) INTO institutions_exist;
    
    IF institutions_exist THEN
        -- Check if the id column is TEXT type
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'institutions'
            AND column_name = 'id'
            AND data_type = 'text'
        ) INTO has_text_id;
        
        IF has_text_id THEN
            -- Create a new foreign key constraint
            EXECUTE 'ALTER TABLE public.accounts
                    ADD CONSTRAINT accounts_institution_id_fkey
                    FOREIGN KEY (institution_id)
                    REFERENCES public.institutions(id)
                    ON DELETE SET NULL';
            RAISE NOTICE 'Created new foreign key constraint with TEXT type';
        ELSE
            RAISE NOTICE 'Not creating foreign key constraint - institutions.id is not TEXT type';
        END IF;
    ELSE
        RAISE NOTICE 'No institutions table found, not creating foreign key constraint';
    END IF;
END $$;

-- Add an index on institution_id for better performance if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'accounts' 
        AND indexname = 'idx_accounts_institution_id'
    ) THEN
        CREATE INDEX idx_accounts_institution_id ON public.accounts(institution_id);
        RAISE NOTICE 'Created index on institution_id column';
    END IF;
END $$; 