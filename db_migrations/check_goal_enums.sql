-- SQL script to check and manage financial_goal enum values

-- Display the current valid enum values
SELECT 
    e.enumlabel AS enum_value,
    e.enumsortorder AS sort_order
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname = 'financial_goal'
ORDER BY e.enumsortorder;

-- Check if the financial_goals table has the column with this enum
SELECT 
    table_name, 
    column_name, 
    data_type, 
    udt_name 
FROM information_schema.columns 
WHERE table_name = 'financial_goals' 
AND column_name = 'goal_type';

-- If you want to add 'other' as a valid enum value later, uncomment this:
/*
DO $$
BEGIN
    -- Check if 'other' is already a value in the enum
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        JOIN pg_enum ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_type.typname = 'financial_goal'
        AND pg_enum.enumlabel = 'other'
    ) THEN
        -- Add 'other' to the enum
        EXECUTE 'ALTER TYPE financial_goal ADD VALUE ''other''';
    END IF;
END
$$;
*/ 