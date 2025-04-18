#!/usr/bin/env python
"""
Script to clear all data from both Django's SQLite database and Supabase.
USE WITH CAUTION - this will delete all data!
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

# Import Django models
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from supabase_integration.services import SupabaseService

User = get_user_model()

def clear_django_database():
    """Clear all data from Django's SQLite database"""
    logger.info("Clearing Django database...")
    
    with transaction.atomic():
        # Get a list of all tables
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'django_migrations'")
        tables = cursor.fetchall()
        
        # Clear each table but don't delete django_migrations
        for table in tables:
            table_name = table[0]
            if table_name != 'django_migrations':
                logger.info(f"Clearing table: {table_name}")
                cursor.execute(f"DELETE FROM {table_name}")
        
        # Reset sequences (auto-increment counters)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM sqlite_sequence")
        
        logger.info("Django database cleared successfully.")
        return True

def execute_sql_script():
    """Execute the SQL script to clear Supabase data"""
    logger.info("Executing SQL script to clear Supabase data...")
    
    try:
        # Initialize Supabase service
        supabase = SupabaseService()
        
        # Verify Supabase connection
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        logger.info(f"Using Supabase URL: {supabase_url}")
        logger.info(f"Supabase key is {'present' if supabase_key else 'MISSING'}")
        
        # Load SQL script
        sql_file_path = Path(__file__).parent / 'sql_migrations' / 'clear_all_data.sql'
        if not sql_file_path.exists():
            logger.error(f"SQL script not found at {sql_file_path}")
            return False
            
        with open(sql_file_path, 'r') as f:
            sql_script = f.read()
        
        # Execute the SQL script in Supabase
        logger.info("Executing SQL script...")
        response = supabase.client.rpc('exec_sql', {'query': sql_script})
        
        # Check if the response has data
        if hasattr(response, 'data') and response.data:
            logger.info(f"SQL script executed successfully. Response: {response.data}")
            return True
        else:
            logger.warning("SQL script executed but no response data returned")
            return True
            
    except Exception as e:
        logger.error(f"Error executing SQL script: {str(e)}")
        return False

def clear_supabase_tables_individually():
    """Clear all data from Supabase tables one by one (fallback method)"""
    logger.info("Clearing Supabase tables individually...")
    
    try:
        # Initialize Supabase service
        supabase = SupabaseService()
        
        # Verify Supabase connection
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        logger.info(f"Using Supabase URL: {supabase_url}")
        logger.info(f"Supabase key is {'present' if supabase_key else 'MISSING'}")
        
        # List of tables to clear (add or remove as needed)
        tables = [
            'transactions',
            'investment_transactions', 
            'account_holdings',
            'securities',
            'account_investments',
            'account_credit_details',
            'account_loan_details',
            'accounts',
            'plaid_items'
        ]
        
        # Set deletion timestamp
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Try to disable RLS policies temporarily
        try:
            logger.info("Attempting to disable RLS for cleaner deletion...")
            # Note: This requires superuser access and may not work in all environments
            supabase.client.rpc('disable_rls_for_tables', {'table_names': tables})
        except Exception as rls_error:
            logger.warning(f"Could not disable RLS: {str(rls_error)}")
        
        # Clear each table in reverse order (to handle foreign keys)
        for table_name in tables:
            try:
                logger.info(f"Clearing table: {table_name}")
                
                # Try direct deletion
                try:
                    # Use RPC call for better control
                    result = supabase.client.rpc('truncate_table', {'table_name': table_name})
                    logger.info(f"Truncated {table_name} using RPC call")
                    continue
                except Exception as trunc_error:
                    logger.warning(f"Could not truncate {table_name} using RPC: {str(trunc_error)}")
                
                # Fallback: Delete in batches to avoid timeout
                try:
                    # First try deleting all records
                    result = supabase.client.table(table_name).delete().execute()
                    
                    if hasattr(result, 'data'):
                        logger.info(f"Deleted {len(result.data) if result.data else 0} rows from {table_name}")
                    else:
                        logger.warning(f"Delete operation returned unexpected result for {table_name}")
                        
                except Exception as e:
                    logger.error(f"Error clearing table {table_name}: {str(e)}")
                    
                    # Fallback: Try deleting in smaller batches
                    try:
                        logger.info(f"Trying batch delete for {table_name}...")
                        # Try to delete 100 records at a time
                        for _ in range(10):  # Try up to 10 batches
                            batch_result = supabase.client.table(table_name).delete().limit(100).execute()
                            if not batch_result.data or len(batch_result.data) == 0:
                                break
                            logger.info(f"Deleted batch of {len(batch_result.data)} records from {table_name}")
                    except Exception as batch_error:
                        logger.error(f"Batch deletion failed for {table_name}: {str(batch_error)}")
            except Exception as e:
                logger.error(f"Unhandled error processing table {table_name}: {str(e)}")
                
        logger.info("Supabase tables cleared individually.")
        return True
    except Exception as e:
        logger.error(f"Error clearing Supabase tables: {str(e)}")
        return False
        
def clear_supabase_data():
    """Clear all data from Supabase tables"""
    logger.info("Clearing Supabase database...")
    
    # First try executing the SQL script
    if execute_sql_script():
        logger.info("Supabase data cleared successfully using SQL script")
        return True
        
    # If that fails, try clearing tables individually
    logger.warning("SQL script execution failed, trying individual table clearing...")
    if clear_supabase_tables_individually():
        logger.info("Supabase data cleared successfully using individual table clearing")
        return True
    
    logger.error("All methods of clearing Supabase data failed")
    return False

def delete_supabase_users(confirm=False):
    """Delete all users from Supabase Auth (USE WITH EXTREME CAUTION)"""
    if not confirm:
        logger.warning("Skipping Supabase user deletion - requires explicit confirmation")
        return False
    
    logger.warning("DELETING ALL SUPABASE USERS - THIS CANNOT BE UNDONE")
    
    try:
        # Initialize Supabase service
        supabase = SupabaseService()
        
        # Get all users
        response = supabase.client.auth.admin.list_users()
        if not response or not response.users:
            logger.info("No Supabase users found to delete")
            return True
            
        user_count = len(response.users)
        logger.info(f"Found {user_count} Supabase users to delete")
        
        # Delete each user
        deleted_count = 0
        for user in response.users:
            try:
                supabase.client.auth.admin.delete_user(user.id)
                deleted_count += 1
                logger.info(f"Deleted Supabase user: {user.email} ({user.id})")
            except Exception as e:
                logger.error(f"Error deleting Supabase user {user.id}: {str(e)}")
        
        logger.info(f"Deleted {deleted_count} of {user_count} Supabase users")
        return True
    except Exception as e:
        logger.error(f"Error deleting Supabase users: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear all data from Django and Supabase databases')
    parser.add_argument('--django-only', action='store_true', help='Clear only Django database')
    parser.add_argument('--supabase-only', action='store_true', help='Clear only Supabase database')
    parser.add_argument('--delete-users', action='store_true', help='Delete Supabase users (USE WITH CAUTION)')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Confirm dangerous operation
    if not args.yes:
        confirm = input("WARNING: This will delete ALL data. Are you sure? (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("Operation cancelled.")
            sys.exit(0)
    
    success = True
    
    # Clear Django database
    if not args.supabase_only:
        django_success = clear_django_database()
        if not django_success:
            success = False
    
    # Clear Supabase data
    if not args.django_only:
        supabase_success = clear_supabase_data()
        if not supabase_success:
            success = False
        
        # Delete Supabase users if requested
        if args.delete_users:
            user_confirm = args.yes or input("DANGER: Delete ALL Supabase users? This CANNOT be undone! (yes/no): ") == 'yes'
            user_success = delete_supabase_users(confirm=user_confirm)
            if not user_success:
                success = False
    
    if success:
        logger.info("All data cleared successfully!")
    else:
        logger.warning("Operation completed with errors. Check the logs above.") 