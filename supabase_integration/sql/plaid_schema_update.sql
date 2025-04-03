-- SQL script to update the plaid_items table schema
-- This script adds the new columns required for our enhanced Plaid refresh strategy

-- Check if plaid_items table exists, create it if it doesn't
CREATE TABLE IF NOT EXISTS plaid_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    access_token TEXT NOT NULL,
    institution_id TEXT,
    institution_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Now add the columns required for our refresh strategy, if they don't exist
DO $$
BEGIN
    -- Add last_successful_update column if it doesn't exist
    IF NOT EXISTS (SELECT FROM information_schema.columns 
                   WHERE table_name = 'plaid_items' AND column_name = 'last_successful_update') THEN
        ALTER TABLE plaid_items ADD COLUMN last_successful_update TIMESTAMPTZ;
    END IF;

    -- Add last_connection_time column if it doesn't exist
    IF NOT EXISTS (SELECT FROM information_schema.columns 
                   WHERE table_name = 'plaid_items' AND column_name = 'last_connection_time') THEN
        ALTER TABLE plaid_items ADD COLUMN last_connection_time TIMESTAMPTZ;
    END IF;
    
    -- Add connection_status column if it doesn't exist
    IF NOT EXISTS (SELECT FROM information_schema.columns 
                   WHERE table_name = 'plaid_items' AND column_name = 'connection_status') THEN
        ALTER TABLE plaid_items ADD COLUMN connection_status TEXT DEFAULT 'active';
    END IF;
    
    -- Add update_type column if it doesn't exist
    IF NOT EXISTS (SELECT FROM information_schema.columns 
                   WHERE table_name = 'plaid_items' AND column_name = 'update_type') THEN
        ALTER TABLE plaid_items ADD COLUMN update_type TEXT DEFAULT 'initial';
    END IF;
    
    -- Add next_hard_refresh column if it doesn't exist
    IF NOT EXISTS (SELECT FROM information_schema.columns 
                   WHERE table_name = 'plaid_items' AND column_name = 'next_hard_refresh') THEN
        ALTER TABLE plaid_items ADD COLUMN next_hard_refresh TIMESTAMPTZ DEFAULT (now() + interval '90 days');
    END IF;
    
    -- Initialize last_successful_update and last_connection_time to now() for existing rows that have NULL values
    UPDATE plaid_items 
    SET last_successful_update = now(),
        last_connection_time = now(),
        connection_status = 'active',
        update_type = 'initial',
        next_hard_refresh = now() + interval '90 days'
    WHERE last_successful_update IS NULL;
    
END $$; 