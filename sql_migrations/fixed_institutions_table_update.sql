-- SQL script to update the institutions table schema (FIXED VERSION)
-- Run this in the Supabase SQL Editor

-- First check if the institutions table exists
DO $$
DECLARE
    institutions_exist boolean := FALSE;
    columns_list text;
BEGIN
    -- Check if institutions table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'institutions'
    ) INTO institutions_exist;
    
    IF institutions_exist THEN
        RAISE NOTICE 'Institutions table found, checking schema...';
        
        -- First, get the list of columns from the existing institutions table
        SELECT string_agg(column_name, ', ') 
        INTO columns_list
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'institutions'
        AND column_name != 'id';
        
        RAISE NOTICE 'Existing columns: %', columns_list;
        
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
            
            -- Create a table to store column definitions
            CREATE TEMP TABLE IF NOT EXISTS temp_columns (
                column_name TEXT,
                column_type TEXT,
                column_default TEXT,
                is_nullable BOOLEAN
            );
            
            -- Get column definitions from the existing table
            INSERT INTO temp_columns
            SELECT 
                column_name,
                data_type,
                column_default,
                is_nullable = 'YES'
            FROM 
                information_schema.columns
            WHERE 
                table_schema = 'public'
                AND table_name = 'institutions'
                AND column_name != 'id';
                
            -- Create the new table dynamically with the same columns but TEXT id
            EXECUTE '
                CREATE TABLE institutions_new (
                    id TEXT PRIMARY KEY
                )
            ';
            
            -- Add all other columns with their original definitions
            FOR i IN 
                SELECT * FROM temp_columns
            LOOP
                EXECUTE format(
                    'ALTER TABLE institutions_new ADD COLUMN %I %s %s %s',
                    i.column_name,
                    i.column_type,
                    CASE WHEN i.column_default IS NOT NULL THEN 'DEFAULT ' || i.column_default ELSE '' END,
                    CASE WHEN i.is_nullable THEN '' ELSE 'NOT NULL' END
                );
            END LOOP;
            
            -- Add any missing essential columns
            IF NOT EXISTS (SELECT 1 FROM temp_columns WHERE column_name = 'created_at') THEN
                ALTER TABLE institutions_new ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM temp_columns WHERE column_name = 'updated_at') THEN
                ALTER TABLE institutions_new ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
            END IF;
            
            -- Now copy the data, build the insert statement dynamically
            EXECUTE format(
                'INSERT INTO institutions_new (id, %s) SELECT id::TEXT, %s FROM institutions',
                columns_list,
                columns_list
            );
            
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
    
    -- Clean up
    DROP TABLE IF EXISTS temp_columns;
END $$; 