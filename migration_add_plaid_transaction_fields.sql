-- Migration to add missing fields to transactions table for Plaid data
-- This will alter the transactions table to include all fields we need for Plaid transactions

-- First, check if the account_name column exists, and add it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'account_name'
    ) THEN
        ALTER TABLE transactions ADD COLUMN account_name TEXT;
    END IF;
END $$;

-- Add other potentially missing fields
DO $$
BEGIN
    -- Account info fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'account_owner'
    ) THEN
        ALTER TABLE transactions ADD COLUMN account_owner TEXT;
    END IF;

    -- Payment details fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'payment_channel'
    ) THEN
        ALTER TABLE transactions ADD COLUMN payment_channel TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'payment_method'
    ) THEN
        ALTER TABLE transactions ADD COLUMN payment_method TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'payee'
    ) THEN
        ALTER TABLE transactions ADD COLUMN payee TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'payer'
    ) THEN
        ALTER TABLE transactions ADD COLUMN payer TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'reference_number'
    ) THEN
        ALTER TABLE transactions ADD COLUMN reference_number TEXT;
    END IF;

    -- Transaction metadata fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'location'
    ) THEN
        ALTER TABLE transactions ADD COLUMN location JSONB;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'website'
    ) THEN
        ALTER TABLE transactions ADD COLUMN website TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'authorized_date'
    ) THEN
        ALTER TABLE transactions ADD COLUMN authorized_date DATE;
    END IF;

    -- Category details
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'category_id'
    ) THEN
        ALTER TABLE transactions ADD COLUMN category_id TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'subcategory'
    ) THEN
        ALTER TABLE transactions ADD COLUMN subcategory TEXT;
    END IF;

    -- Currency information
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'iso_currency_code'
    ) THEN
        ALTER TABLE transactions ADD COLUMN iso_currency_code TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'unofficial_currency_code'
    ) THEN
        ALTER TABLE transactions ADD COLUMN unofficial_currency_code TEXT;
    END IF;

    -- Check if user_id column exists, add it if it doesn't - without foreign key constraint
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE transactions ADD COLUMN user_id UUID;
        RAISE NOTICE 'Added user_id column to transactions table';
    END IF;

    -- Add 'name' column for transaction name if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'name'
    ) THEN
        ALTER TABLE transactions ADD COLUMN name TEXT;
        RAISE NOTICE 'Added name column to transactions table';
    END IF;

    -- Add index on account_id for faster lookups
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'transactions' AND indexname = 'idx_transactions_account_id'
    ) THEN
        CREATE INDEX idx_transactions_account_id ON transactions(account_id);
    END IF;

    -- Add index on user_id for faster lookups, but only if the column exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'user_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'transactions' AND indexname = 'idx_transactions_user_id'
    ) THEN
        CREATE INDEX idx_transactions_user_id ON transactions(user_id);
    END IF;

    -- Add index on date for faster date range queries
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'transactions' AND indexname = 'idx_transactions_date'
    ) THEN
        CREATE INDEX idx_transactions_date ON transactions(date);
    END IF;
END $$;

-- Add comment describing the table
COMMENT ON TABLE transactions IS 'Stores financial transactions, including data from Plaid API'; 