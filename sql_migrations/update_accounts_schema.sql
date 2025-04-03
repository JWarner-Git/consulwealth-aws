-- SQL script to update the accounts table schema
-- Run this in the Supabase SQL Editor

-- Create the accounts table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT,
    subtype TEXT,
    current_balance NUMERIC DEFAULT 0,
    available_balance NUMERIC DEFAULT 0,
    institution_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Check for and handle any foreign key constraints on institution_id
DO $$
DECLARE
    constraint_name text;
BEGIN
    -- Check if there's a foreign key constraint on institution_id
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'public.accounts'::regclass
    AND conname LIKE '%institution_id%';
    
    IF constraint_name IS NOT NULL THEN
        -- Drop the existing foreign key constraint
        EXECUTE 'ALTER TABLE public.accounts DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped foreign key constraint: %', constraint_name;
    END IF;
END $$;

-- Ensure institution_id is TEXT type (in case it was defined as UUID incorrectly)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'institution_id'
        AND data_type <> 'text'
    ) THEN
        ALTER TABLE public.accounts 
        ALTER COLUMN institution_id TYPE TEXT USING institution_id::TEXT;
        RAISE NOTICE 'Changed institution_id column type to TEXT';
    END IF;
END $$;

-- Add missing columns for general account fields
DO $$
BEGIN
    -- Add mask column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'mask'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN mask TEXT;
    END IF;

    -- Add official_name column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'official_name'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN official_name TEXT;
    END IF;

    -- Add limit column if it doesn't exist (renamed to account_limit to avoid reserved word)
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'limit'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN "limit" NUMERIC;
    END IF;

    -- Add iso_currency_code column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'iso_currency_code'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN iso_currency_code TEXT;
    END IF;

    -- Add last_updated column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'last_updated'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN last_updated TIMESTAMPTZ DEFAULT NOW();
    END IF;

    -- Add is_deleted column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_deleted'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
    END IF;

    -- Add is_hidden column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_hidden'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE;
    END IF;

    -- Add plaid_account_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'plaid_account_id'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN plaid_account_id TEXT;
    END IF;
END $$;

-- Add columns for investment accounts
DO $$
BEGIN
    -- Add is_investment_account column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_investment_account'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_investment_account BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Add columns for debt accounts (credit cards, loans, etc.)
DO $$
BEGIN
    -- Add is_debt_account column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'is_debt_account'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN is_debt_account BOOLEAN DEFAULT FALSE;
    END IF;

    -- Add debt_type column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'debt_type'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN debt_type TEXT; -- credit_card, mortgage, student_loan, etc.
    END IF;

    -- Add interest_rate column if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'interest_rate'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN interest_rate NUMERIC;
    END IF;

    -- Add credit card specific columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'late_fee'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN late_fee NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'minimum_payment'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN minimum_payment NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'payment_due_date'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN payment_due_date DATE;
    END IF;

    -- Add loan specific columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'maturity_date'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN maturity_date DATE;
    END IF;

    -- Add credit limit related columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'available_credit'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN available_credit NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'credit_limit'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN credit_limit NUMERIC;
    END IF;

    -- Add loan balance columns
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'loan_balance'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN loan_balance NUMERIC;
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'origination_date'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN origination_date DATE;
    END IF;

    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'accounts'
        AND column_name = 'payment_amount'
    ) THEN
        ALTER TABLE public.accounts ADD COLUMN payment_amount NUMERIC;
    END IF;
END $$;

-- Add indexes for performance
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'accounts' 
        AND indexname = 'idx_accounts_user_id'
    ) THEN
        CREATE INDEX idx_accounts_user_id ON public.accounts(user_id);
        RAISE NOTICE 'Created index on user_id column';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'accounts' 
        AND indexname = 'idx_accounts_account_id'
    ) THEN
        CREATE INDEX idx_accounts_account_id ON public.accounts(account_id);
        RAISE NOTICE 'Created index on account_id column';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'accounts' 
        AND indexname = 'idx_accounts_institution_id'
    ) THEN
        CREATE INDEX idx_accounts_institution_id ON public.accounts(institution_id);
        RAISE NOTICE 'Created index on institution_id column';
    END IF;
END $$; 