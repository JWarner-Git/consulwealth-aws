-- Migration to add goal deduplication via client request ID
-- Creates a function to find recently created goals with the same client_request_id

-- Create the function to find goals by client_request_id in metadata
CREATE OR REPLACE FUNCTION find_goal_by_client_request_id(
    p_user_id UUID,
    p_client_request_id TEXT,
    p_minutes INTEGER DEFAULT 10
)
RETURNS SETOF financial_goals AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM financial_goals
    WHERE user_id = p_user_id
    AND metadata->>'client_request_id' = p_client_request_id
    AND created_at >= (NOW() - (p_minutes || ' minutes')::INTERVAL)
    ORDER BY created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add metadata column to financial_goals if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'financial_goals' 
        AND column_name = 'metadata'
    ) THEN
        ALTER TABLE financial_goals ADD COLUMN metadata JSONB DEFAULT '{}'::JSONB;
    END IF;
END $$; 