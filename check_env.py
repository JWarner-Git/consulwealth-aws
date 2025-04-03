"""
Check environment variables loading from .env file
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / '.env'
print(f"Looking for .env file at: {env_path} (exists: {env_path.exists()})")
load_dotenv(dotenv_path=env_path)

# Print Plaid environment variables
print("\nPlaid Environment Variables:")
print(f"PLAID_CLIENT_ID: {os.environ.get('PLAID_CLIENT_ID', 'NOT SET')}")
print(f"PLAID_SECRET: {os.environ.get('PLAID_SECRET', 'NOT SET')}")
print(f"PLAID_ENVIRONMENT: {os.environ.get('PLAID_ENVIRONMENT', 'NOT SET')}")

# Print Supabase environment variables
print("\nSupabase Environment Variables:")
print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL', 'NOT SET')}")
print(f"SUPABASE_KEY: {os.environ.get('SUPABASE_KEY', 'NOT SET')}")
print(f"SUPABASE_SERVICE_KEY: {os.environ.get('SUPABASE_SERVICE_KEY', 'NOT SET')}")

print("\nIf variables show 'NOT SET', check that your .env file is in the correct location and properly formatted.")
print("The .env file should be directly in the clean_backend directory.") 