-- Migration to add 'home' as a valid value to the financial_goal enum type
-- Used for financial goals related to home down payments

-- Add 'home' to the financial_goal enum type if it doesn't exist
DO $$
BEGIN
    -- Check if 'home' is already a value in the enum
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        JOIN pg_enum ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_type.typname = 'financial_goal'
        AND pg_enum.enumlabel = 'home'
    ) THEN
        -- Add 'home' to the enum
        EXECUTE 'ALTER TYPE financial_goal ADD VALUE ''home''';
    END IF;
END
$$; 