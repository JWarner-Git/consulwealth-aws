-- SQL script to check the current database schema
-- Run this in the Supabase SQL Editor to diagnose issues

-- Check for the institutions table
SELECT 
    EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'institutions'
    ) AS institutions_table_exists;

-- Check if the institutions table exists, get its columns
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'institutions'
    ) THEN
        RAISE NOTICE 'Institutions table columns:';
        
        FOR col_rec IN
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'institutions'
            ORDER BY ordinal_position
        LOOP
            RAISE NOTICE '  - % (type: %, nullable: %)', 
                col_rec.column_name, col_rec.data_type, col_rec.is_nullable;
        END LOOP;
    ELSE
        RAISE NOTICE 'Institutions table does not exist';
    END IF;
END $$;

-- Check for the accounts table
SELECT 
    EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'accounts'
    ) AS accounts_table_exists;

-- Check if the accounts table exists, look at institution_id column
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'accounts'
    ) THEN
        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'accounts'
            AND column_name = 'institution_id'
        ) THEN
            SELECT data_type INTO STRICT data_type_var
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'accounts'
            AND column_name = 'institution_id';
            
            RAISE NOTICE 'Accounts table has institution_id column with type: %', data_type_var;
        ELSE
            RAISE NOTICE 'Accounts table exists but has no institution_id column';
        END IF;
    ELSE
        RAISE NOTICE 'Accounts table does not exist';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error checking institution_id column: %', SQLERRM;
END $$;

-- Check foreign key constraints
DO $$
BEGIN
    FOR constraint_rec IN
        SELECT
            tc.constraint_name,
            tc.table_name AS src_table,
            kcu.column_name AS src_column,
            ccu.table_name AS ref_table,
            ccu.column_name AS ref_column
        FROM
            information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE
            tc.constraint_type = 'FOREIGN KEY'
            AND (
                (tc.table_name = 'accounts' AND kcu.column_name = 'institution_id')
                OR (ccu.table_name = 'institutions')
            )
    LOOP
        RAISE NOTICE 'Foreign key: % links %.% to %.%',
            constraint_rec.constraint_name,
            constraint_rec.src_table, constraint_rec.src_column,
            constraint_rec.ref_table, constraint_rec.ref_column;
    END LOOP;
END $$; 