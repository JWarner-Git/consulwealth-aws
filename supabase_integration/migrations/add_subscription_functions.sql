-- Function to execute raw SQL queries
-- This is a general-purpose function for executing SQL queries
-- SECURITY WARNING: Only use this for controlled administrative tasks
CREATE OR REPLACE FUNCTION execute_sql(query text)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE query;
END;
$$;

-- Function to update subscription status by ID
-- This is a safer approach than raw SQL execution
CREATE OR REPLACE FUNCTION update_subscription_status(
  user_id UUID,
  is_premium BOOLEAN,
  plan TEXT,
  status TEXT,
  end_date TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE profiles
  SET 
    is_premium_subscriber = is_premium,
    subscription_plan = plan,
    subscription_status = status,
    subscription_end_date = end_date::TIMESTAMPTZ
  WHERE id = user_id;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION execute_sql TO service_role;
GRANT EXECUTE ON FUNCTION update_subscription_status TO service_role; 