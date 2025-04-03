-- Direct SQL script to completely clear all Plaid data
-- Copy and paste this entire script into the Supabase SQL Editor and run it

-- Start a transaction for safety
BEGIN;

-- Disable triggers to avoid foreign key issues
SET session_replication_role = 'replica';

-- Delete all data from Plaid-related tables in the correct order
DELETE FROM public.investment_transactions;
DELETE FROM public.transactions;
DELETE FROM public.account_holdings;
DELETE FROM public.securities;
DELETE FROM public.account_investments;
DELETE FROM public.account_credit_details; 
DELETE FROM public.account_loan_details;
DELETE FROM public.accounts;
DELETE FROM public.plaid_items;

-- Re-enable triggers
SET session_replication_role = 'origin';

-- Show the current counts from each table to verify
SELECT 'plaid_items' as table_name, COUNT(*) as count FROM public.plaid_items UNION ALL
SELECT 'accounts' as table_name, COUNT(*) as count FROM public.accounts UNION ALL
SELECT 'transactions' as table_name, COUNT(*) as count FROM public.transactions UNION ALL
SELECT 'investment_transactions' as table_name, COUNT(*) as count FROM public.investment_transactions UNION ALL
SELECT 'account_holdings' as table_name, COUNT(*) as count FROM public.account_holdings UNION ALL
SELECT 'securities' as table_name, COUNT(*) as count FROM public.securities UNION ALL
SELECT 'account_investments' as table_name, COUNT(*) as count FROM public.account_investments UNION ALL
SELECT 'account_credit_details' as table_name, COUNT(*) as count FROM public.account_credit_details UNION ALL
SELECT 'account_loan_details' as table_name, COUNT(*) as count FROM public.account_loan_details;

-- Commit the transaction
COMMIT; 