-- Comprehensive migration to add all necessary goal types to the financial_goal enum

-- First, let's add a function that can safely add enum values without erroring if they exist
CREATE OR REPLACE FUNCTION add_enum_value(enum_type text, enum_value text) 
RETURNS void AS $$
BEGIN
    -- Check if the value already exists in the enum
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = enum_type
        AND e.enumlabel = enum_value
    ) THEN
        -- Add the value to the enum
        EXECUTE format('ALTER TYPE %I ADD VALUE %L', enum_type, enum_value);
        RAISE NOTICE 'Added % to enum %', enum_value, enum_type;
    ELSE
        RAISE NOTICE 'Value % already exists in enum %', enum_value, enum_type;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Now add all the needed goal types
SELECT add_enum_value('financial_goal', 'emergency');
SELECT add_enum_value('financial_goal', 'retirement');
SELECT add_enum_value('financial_goal', 'education');
SELECT add_enum_value('financial_goal', 'other');
SELECT add_enum_value('financial_goal', 'vacation');
SELECT add_enum_value('financial_goal', 'vehicle');
SELECT add_enum_value('financial_goal', 'investment');
SELECT add_enum_value('financial_goal', 'home');
SELECT add_enum_value('financial_goal', 'wedding');
SELECT add_enum_value('financial_goal', 'health');

-- Display the updated enum values
SELECT 
    e.enumlabel AS enum_value,
    e.enumsortorder AS sort_order
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname = 'financial_goal'
ORDER BY e.enumsortorder; 