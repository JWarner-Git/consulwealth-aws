#!/usr/bin/env python
"""
Script to fix missing user_id in transactions table.
This script will add user_id to all transactions based on their account_id.
"""
import os
import sys
import django
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from supabase_integration.adapter import SupabaseAdapter

def fix_transaction_user_ids():
    """Find transactions without user_id and add the correct user_id based on account relationship"""
    adapter = SupabaseAdapter()
    
    # Get all accounts with their user_id
    logger.info("Fetching all accounts...")
    all_accounts_response = adapter.client.table('accounts').select('id, account_id, user_id').execute()
    
    if not all_accounts_response.data:
        logger.error("No accounts found in the database")
        return False
        
    # Create a mapping of account_id to user_id
    account_to_user_map = {}
    for account in all_accounts_response.data:
        if 'id' in account and 'user_id' in account:
            account_to_user_map[account['id']] = account['user_id']
        if 'account_id' in account and account['account_id'] and 'user_id' in account:
            account_to_user_map[account['account_id']] = account['user_id']
    
    logger.info(f"Found {len(account_to_user_map)} account-to-user mappings")
    
    # Get all transactions without user_id
    logger.info("Fetching transactions without user_id...")
    transactions_response = adapter.client.table('transactions').select('id, account_id').is_('user_id', 'null').execute()
    
    if not transactions_response.data:
        logger.info("No transactions found without user_id")
        return True
    
    logger.info(f"Found {len(transactions_response.data)} transactions without user_id")
    
    # Update transactions with missing user_id
    updated_count = 0
    for transaction in transactions_response.data:
        if 'id' in transaction and 'account_id' in transaction and transaction['account_id'] in account_to_user_map:
            transaction_id = transaction['id']
            account_id = transaction['account_id']
            user_id = account_to_user_map[account_id]
            
            try:
                # Update the transaction with the user_id
                update_response = adapter.client.table('transactions').update({'user_id': user_id}).eq('id', transaction_id).execute()
                
                if update_response.data:
                    updated_count += 1
                else:
                    logger.warning(f"Failed to update transaction {transaction_id}")
            except Exception as e:
                logger.error(f"Error updating transaction {transaction_id}: {str(e)}")
    
    logger.info(f"Updated {updated_count} of {len(transactions_response.data)} transactions with missing user_id")
    return True

if __name__ == "__main__":
    logger.info("Starting transaction user_id fix script...")
    success = fix_transaction_user_ids()
    
    if success:
        logger.info("Transaction fix completed successfully")
    else:
        logger.error("Transaction fix failed")
        sys.exit(1) 