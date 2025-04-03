#!/usr/bin/env python
"""
Test script to verify Supabase initialization with environment variables.
Run this script directly to test if Supabase can be properly initialized.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up the environment by loading variables from .env file"""
    # Get the directory containing this script
    script_dir = Path(__file__).resolve().parent
    
    # Find and load .env file
    env_path = script_dir / '.env'
    if env_path.exists():
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(dotenv_path=env_path)
    else:
        logger.error(f".env file not found at {env_path}")
        return False
    
    return True

def test_supabase_connection():
    """Test the connection to Supabase"""
    # Get Supabase credentials from environment
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    # Check if credentials are available
    logger.info(f"SUPABASE_URL: {'Set' if supabase_url else 'NOT SET'}")
    logger.info(f"SUPABASE_KEY: {'Set' if supabase_key else 'NOT SET'}")
    logger.info(f"SUPABASE_SERVICE_KEY: {'Set' if service_key else 'NOT SET'}")
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials are not properly set in environment variables")
        return False
    
    # Test with anon key (for standard auth)
    try:
        logger.info("Testing Supabase connection with anon key...")
        supabase_client = create_client(supabase_url, supabase_key)
        
        # Try a simple operation
        response = supabase_client.table('accounts').select('count', count='exact').limit(1).execute()
        count = response.count if hasattr(response, 'count') else "unknown"
        logger.info(f"Connection successful! Found {count} accounts in database.")
        
        auth_client = supabase_client.auth
        logger.info(f"Auth client: {auth_client is not None}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Supabase connection: {str(e)}")
        return False
        
    # Test with service key (for admin operations)
    if service_key:
        try:
            logger.info("Testing Supabase connection with service key...")
            admin_client = create_client(supabase_url, service_key)
            
            # Try to list users (admin-only operation)
            try:
                users = admin_client.auth.admin.list_users()
                logger.info(f"Admin connection successful! Found {len(users.users) if users and hasattr(users, 'users') else 0} users.")
            except Exception as e:
                logger.error(f"Error listing users: {str(e)}")
                
            return True
        except Exception as e:
            logger.error(f"Error testing Supabase admin connection: {str(e)}")
            return False

def main():
    """Main entry point"""
    logger.info("Starting Supabase connection test")
    
    # Set up environment
    if not setup_environment():
        logger.error("Failed to set up environment")
        return 1
    
    # Test Supabase connection
    if test_supabase_connection():
        logger.info("All tests completed successfully!")
        return 0
    else:
        logger.error("Tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 