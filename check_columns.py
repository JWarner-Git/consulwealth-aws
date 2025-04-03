"""
Script to verify all necessary columns exist in the accounts table
after running SQL migrations
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / '.env'
print(f"Loading .env from: {env_path} (exists: {env_path.exists()})")
load_dotenv(dotenv_path=env_path)

from supabase import create_client

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("Missing Supabase credentials in .env file")
    sys.exit(1)

print(f"Connecting to Supabase at {supabase_url}")
client = create_client(supabase_url, supabase_key)

# Required columns for accounts table
REQUIRED_COLUMNS = [
    'id', 'user_id', 'institution_id', 'account_id', 'name', 
    'type', 'subtype', 'current_balance', 'available_balance',
    'is_investment', 'is_investment_account', 'is_credit', 'is_loan', 'is_depository',
    'is_auth', 'is_authenticated', 'is_plaid_synced', 'status',
    'color', 'icon_url', 'plaid_item_id', 'portfolio_value', 'last_updated',
    'loan_type', 'loan_term', 'loan_rate'
]

# Query the accounts table to get column names
try:
    response = client.rpc(
        'execute_sql', 
        {'sql': "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'accounts' AND table_schema = 'public' ORDER BY ordinal_position;"}
    ).execute()
    
    if hasattr(response, 'data') and response.data:
        # Get the column names from the response
        existing_columns = {col['column_name'] for col in response.data}
        
        print("\n=== ACCOUNTS TABLE COLUMN CHECK ===")
        
        # Check missing columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in existing_columns]
        if missing_columns:
            print(f"\n❌ Missing columns: {', '.join(missing_columns)}")
        else:
            print("\n✅ All required columns exist in the accounts table!")
        
        # Check types for sensitive columns
        for col in response.data:
            if col['column_name'] == 'plaid_item_id' and col['data_type'] == 'uuid':
                print(f"\n⚠️ WARNING: plaid_item_id is of type UUID but should be TEXT")
        
        # Print all columns and their types
        print("\n--- Current Account Table Schema ---")
        for col in response.data:
            print(f"- {col['column_name']} ({col['data_type']})")
        
        # Print a summary
        print(f"\nTotal columns: {len(existing_columns)}")
        print(f"Required columns: {len(REQUIRED_COLUMNS)}")
        print(f"Extra columns: {len(existing_columns) - len(REQUIRED_COLUMNS)}")
        
    else:
        print("No schema data returned. Check if you have appropriate permissions.")
        
except Exception as e:
    print(f"Error querying database schema: {str(e)}")
    print("Try running the SQL migrations again or check your database connection.") 