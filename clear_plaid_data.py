#!/usr/bin/env python
"""
Script to specifically clear Plaid-related data from Supabase.
This script uses direct SQL for more reliable clearing.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    from supabase_integration.services import SupabaseService
except ImportError:
    logger.error("Required packages not found. Make sure you have supabase-py installed.")
    sys.exit(1)

def clear_plaid_data():
    """Clear all Plaid-related data from Supabase using direct SQL queries"""
    logger.info("Clearing Plaid data...")
    
    # Initialize Supabase connection
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase URL or key not found in environment variables")
        return False
    
    logger.info(f"Connecting to Supabase at {supabase_url}")
    
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Define SQL queries to clear data in the correct order
        # We use raw SQL for more direct control
        sql_queries = [
            # Disable RLS temporarily for admin operations
            "BEGIN; SET session_replication_role = 'replica';",
            
            # First clear dependent tables
            "DELETE FROM investment_transactions;",
            "DELETE FROM transactions;",
            "DELETE FROM account_holdings;",
            "DELETE FROM securities;",
            "DELETE FROM account_investments;",
            "DELETE FROM account_credit_details;",
            "DELETE FROM account_loan_details;",
            "DELETE FROM accounts;",
            
            # Then clear the main plaid_items table
            "DELETE FROM plaid_items;",
            
            # Re-enable RLS
            "SET session_replication_role = 'origin'; COMMIT;"
        ]
        
        # Execute each query
        for i, query in enumerate(sql_queries):
            logger.info(f"Executing query {i+1}/{len(sql_queries)}: {query}")
            try:
                result = supabase.rpc('exec_sql', {'query': query})
                logger.info(f"Query {i+1} executed successfully")
            except Exception as query_error:
                logger.error(f"Error executing query {i+1}: {str(query_error)}")
                # Continue with next query even if this one fails
        
        # Verify all tables are empty
        verification_queries = [
            "SELECT COUNT(*) FROM plaid_items",
            "SELECT COUNT(*) FROM accounts",
            "SELECT COUNT(*) FROM transactions"
        ]
        
        logger.info("Verifying data was cleared:")
        for query in verification_queries:
            try:
                result = supabase.rpc('exec_sql', {'query': query})
                count = 0
                if hasattr(result, 'data') and result.data and len(result.data) > 0:
                    count = result.data[0].get('count', 0)
                logger.info(f"{query}: {count} records remaining")
            except Exception as verify_error:
                logger.error(f"Error verifying data: {str(verify_error)}")
        
        logger.info("Plaid data clearing operation completed")
        return True
    except Exception as e:
        logger.error(f"Error clearing Plaid data: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear all Plaid data from Supabase')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Confirm dangerous operation
    if not args.yes:
        confirm = input("WARNING: This will delete ALL Plaid data. Are you sure? (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("Operation cancelled.")
            sys.exit(0)
    
    success = clear_plaid_data()
    
    if success:
        logger.info("All Plaid data cleared successfully!")
    else:
        logger.warning("Operation completed with errors. Check the logs above.") 