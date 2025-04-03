"""
Script to check the database schema of the accounts table
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

# Query the accounts table to get column names
try:
    response = client.table('accounts').select('*').limit(1).execute()
    
    if response.data:
        print("\nAccounts table columns:")
        account = response.data[0]
        for column in account.keys():
            print(f"- {column}")
    else:
        print("\nNo accounts found in the database.")
        
        # Try to run SQL query to get column names directly
        print("\nAttempting to get columns directly from schema:")
        response = client.rpc('get_columns', {'table_name': 'accounts'}).execute()
        print(response)
        
except Exception as e:
    print(f"Error querying accounts table: {str(e)}")
    
    # Try a special function to get column names
    try:
        print("\nTrying to run raw SQL to get column definitions:")
        response = client.rpc(
            'execute_sql', 
            {'sql': "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'accounts' AND table_schema = 'public' ORDER BY ordinal_position;"}
        ).execute()
        print(response)
    except Exception as sql_e:
        print(f"Error running SQL query: {str(sql_e)}") 