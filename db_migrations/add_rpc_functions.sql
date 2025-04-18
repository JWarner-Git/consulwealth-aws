-- Migration to add RPC functions for financial goals management

-- Function to find goals by client_request_id in metadata
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

-- Function to add funds to a goal
CREATE OR REPLACE FUNCTION add_funds_to_goal(
    p_goal_id UUID,
    p_amount NUMERIC,
    p_notes TEXT DEFAULT NULL
)
RETURNS TABLE(
    goal_id UUID,
    transaction_id UUID,
    new_amount NUMERIC,
    success BOOLEAN
) AS $$
DECLARE
    v_transaction_id UUID;
    v_new_amount NUMERIC;
    v_success BOOLEAN := FALSE;
BEGIN
    -- Insert the transaction
    INSERT INTO goal_transactions(
        goal_id,
        amount,
        transaction_type,
        notes
    ) VALUES (
        p_goal_id,
        p_amount,
        'deposit',
        p_notes
    ) RETURNING id INTO v_transaction_id;
    
    -- Update the goal's current amount
    UPDATE financial_goals
    SET 
        current_amount = current_amount + p_amount,
        updated_at = NOW()
    WHERE id = p_goal_id
    RETURNING current_amount INTO v_new_amount;
    
    -- Set success flag
    v_success := TRUE;
    
    -- Return the results
    RETURN QUERY
    SELECT 
        p_goal_id,
        v_transaction_id,
        v_new_amount,
        v_success;
    
EXCEPTION WHEN OTHERS THEN
    -- Return with failure
    RETURN QUERY
    SELECT 
        p_goal_id,
        NULL::UUID,
        0::NUMERIC,
        FALSE;
END;
$$ LANGUAGE plpgsql; 