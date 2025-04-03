-- Verify schema changes for Plaid integration
-- Run this in the Supabase SQL Editor to check if your schema updates were applied correctly

-- Check plaid_items table
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'plaid_items'
) AS plaid_items_table_exists;

-- Check plaid_items columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'plaid_items'
ORDER BY ordinal_position;

-- Check accounts table
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'accounts'
) AS accounts_table_exists;

-- Check accounts columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'accounts'
ORDER BY ordinal_position;

-- Check institutions table if it exists
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'institutions'
) AS institutions_table_exists;

-- Check institutions columns if table exists
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'institutions'
    ) THEN
        CREATE TEMP TABLE temp_institutions_columns AS
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'institutions'
        ORDER BY ordinal_position;
    END IF;
END $$;

SELECT * FROM temp_institutions_columns WHERE EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'temp' 
    AND table_name = 'temp_institutions_columns'
);

-- Check constraints on accounts table
SELECT tc.constraint_name, tc.constraint_type, 
       kcu.column_name, 
       ccu.table_name AS foreign_table_name, 
       ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'accounts'
AND tc.table_schema = 'public'
ORDER BY tc.constraint_name; 