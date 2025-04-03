-- SQL script to reset all Plaid refresh timers
-- Run this in the Supabase SQL Editor if you need to immediately force all items to be eligible for refresh

-- For safety, first check if the columns exist
DO $$
BEGIN
    -- Check if the necessary columns exist
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'plaid_items'
        AND column_name = 'last_successful_update'
    ) THEN
        -- Set last_successful_update to 8 days ago (soft refresh interval is 7 days)
        UPDATE public.plaid_items 
        SET last_successful_update = NOW() - INTERVAL '8 days';
        
        RAISE NOTICE 'Reset last_successful_update timestamps for all Plaid items';
    ELSE
        RAISE NOTICE 'The last_successful_update column does not exist';
    END IF;
    
    -- Check if next_hard_refresh column exists
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'plaid_items'
        AND column_name = 'next_hard_refresh'
    ) THEN
        -- Set next_hard_refresh to yesterday (forcing hard refresh eligibility)
        UPDATE public.plaid_items 
        SET next_hard_refresh = NOW() - INTERVAL '1 day';
        
        RAISE NOTICE 'Reset next_hard_refresh timestamps for all Plaid items';
    ELSE
        RAISE NOTICE 'The next_hard_refresh column does not exist';
    END IF;
END $$;

-- Verify by showing all items with their new timestamps
SELECT 
    id, 
    item_id, 
    last_successful_update, 
    next_hard_refresh 
FROM 
    public.plaid_items; 