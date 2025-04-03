-- SQL script to create tables for investment holdings and securities
-- This script is safe to run multiple times as it checks if tables exist before creating them

-- Create the UUID extension if it doesn't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create or update the securities table
CREATE TABLE IF NOT EXISTS public.securities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    security_id TEXT NOT NULL,
    name TEXT,
    ticker_symbol TEXT,
    isin TEXT,
    cusip TEXT,
    type TEXT,
    close_price NUMERIC,
    close_price_as_of TIMESTAMP WITH TIME ZONE,
    currency_code TEXT DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create an index on security_id for faster lookup (if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_securities_security_id ON public.securities(security_id);

-- Add a comment for documentation
COMMENT ON TABLE public.securities IS 'Stores information about securities obtained from Plaid''s investments API';

-- Create the updated_at function if it doesn't exist
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger for securities if it doesn't exist
DROP TRIGGER IF EXISTS set_updated_at_securities ON public.securities;
CREATE TRIGGER set_updated_at_securities
BEFORE UPDATE ON public.securities
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Create account_holdings table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.account_holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL,
    security_id UUID NOT NULL,
    cost_basis NUMERIC,
    quantity NUMERIC,
    institution_value NUMERIC,
    institution_price NUMERIC,
    institution_price_as_of TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT fk_account
        FOREIGN KEY (account_id)
        REFERENCES public.accounts(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_security
        FOREIGN KEY (security_id)
        REFERENCES public.securities(id)
        ON DELETE CASCADE
);

-- Create indexes for faster joins and lookups
CREATE INDEX IF NOT EXISTS idx_account_holdings_account_id ON public.account_holdings(account_id);
CREATE INDEX IF NOT EXISTS idx_account_holdings_security_id ON public.account_holdings(security_id);

-- Add a comment for documentation
COMMENT ON TABLE public.account_holdings IS 'Stores holdings information linking accounts with securities';

-- Create the trigger for account_holdings if it doesn't exist
DROP TRIGGER IF EXISTS set_updated_at_account_holdings ON public.account_holdings;
CREATE TRIGGER set_updated_at_account_holdings
BEFORE UPDATE ON public.account_holdings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Add column to accounts table to indicate if it's an investment account (if it doesn't exist)
ALTER TABLE public.accounts ADD COLUMN IF NOT EXISTS is_investment_account BOOLEAN DEFAULT FALSE;

-- Add investment-specific column for portfolio value (if it doesn't exist)
ALTER TABLE public.accounts ADD COLUMN IF NOT EXISTS portfolio_value NUMERIC; 