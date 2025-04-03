-- SQL script to update the institutions table schema if it exists
-- Run this in the Supabase SQL Editor

-- First check if the institutions table exists
DO $$
DECLARE
    institutions_exist boolean := FALSE;
BEGIN
    -- Check if institutions table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'institutions'
    ) INTO institutions_exist;
    
    IF institutions_exist THEN
        RAISE NOTICE 'Institutions table found, checking schema...';
        
        -- Check if the id column is TEXT or UUID
        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'institutions'
            AND column_name = 'id'
            AND data_type = 'uuid'
        ) THEN
            -- Create a backup of the table
            EXECUTE 'CREATE TABLE IF NOT EXISTS institutions_backup AS SELECT * FROM institutions';
            RAISE NOTICE 'Created backup of institutions table';
            
            -- Modify the table to handle Plaid institution_ids
            RAISE NOTICE 'Modifying institutions table to use TEXT ids instead of UUIDs to match Plaid institution IDs...';
            
            -- Check if there are relationships with accounts.institution_id
            IF EXISTS (
                SELECT FROM pg_constraint
                WHERE conrelid = 'public.accounts'::regclass
                AND conname LIKE '%institution_id%'
            ) THEN
                -- Drop any foreign key constraints that might exist
                BEGIN
                    EXECUTE 'ALTER TABLE public.accounts DROP CONSTRAINT accounts_institution_id_fkey';
                    RAISE NOTICE 'Dropped foreign key constraint from accounts table';
                EXCEPTION
                    WHEN OTHERS THEN
                        RAISE NOTICE 'No constraint named accounts_institution_id_fkey found';
                END;
            END IF;
            
            -- Create a new institutions table with TEXT id
            EXECUTE '
                CREATE TABLE institutions_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    logo TEXT,
                    website TEXT,
                    description TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            ';
            
            -- Get column names from the existing institutions table
            DECLARE
                columns_to_copy TEXT;
            BEGIN
                SELECT string_agg(column_name, ', ')
                INTO columns_to_copy
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'institutions'
                AND column_name != 'id';
                
                -- Insert data from old table, converting UUID to TEXT
                IF columns_to_copy IS NOT NULL THEN
                    EXECUTE 'INSERT INTO institutions_new (id, ' || columns_to_copy || ')
                            SELECT id::TEXT, ' || columns_to_copy || ' FROM institutions';
                ELSE
                    EXECUTE 'INSERT INTO institutions_new (id)
                            SELECT id::TEXT FROM institutions';
                END IF;
            END;
            
            -- Drop the old table and rename the new one
            EXECUTE 'DROP TABLE institutions';
            EXECUTE 'ALTER TABLE institutions_new RENAME TO institutions';
            
            -- Add an appropriate index
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_institutions_name ON institutions(name)';
            
            RAISE NOTICE 'Successfully updated institutions table to use TEXT ids';
        ELSE
            RAISE NOTICE 'Institutions table already uses TEXT ids, no changes needed';
        END IF;
        
        -- Now attempt to restore the foreign key relationship
        BEGIN
            EXECUTE 'ALTER TABLE public.accounts
                    ADD CONSTRAINT accounts_institution_id_fkey
                    FOREIGN KEY (institution_id)
                    REFERENCES public.institutions(id)
                    ON DELETE SET NULL';
            RAISE NOTICE 'Created foreign key constraint on accounts.institution_id';
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Could not create foreign key constraint: %', SQLERRM;
        END;
    ELSE
        RAISE NOTICE 'No institutions table found in the database';
    END IF;
END $$; 