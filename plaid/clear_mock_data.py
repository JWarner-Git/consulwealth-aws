#!/usr/bin/env python
"""
Script to clear mock Plaid data from Supabase.
Run this script to delete all mock accounts and transactions.
"""
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from plaid.services import PlaidService

User = get_user_model()

def clear_mock_data_for_user(user_email):
    """Clear all mock Plaid data for a specific user"""
    try:
        user = User.objects.get(email=user_email)
        service = PlaidService(use_mock_data=False)  # Set use_mock_data to False
        
        print(f"Clearing mock data for user: {user.email}")
        success = service.clear_user_data(user)
        
        if success:
            print(f"Successfully cleared all mock Plaid data for user: {user.email}")
        else:
            print(f"Failed to clear data for user: {user.email}")
            
        return success
    except User.DoesNotExist:
        print(f"User with email {user_email} does not exist")
        return False
    except Exception as e:
        print(f"Error clearing data: {str(e)}")
        return False

def clear_mock_data_for_all_users():
    """Clear all mock Plaid data for all users"""
    print("Clearing mock data for all users...")
    users = User.objects.all()
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        print(f"Processing user: {user.email}")
        service = PlaidService(use_mock_data=False)  # Set use_mock_data to False
        success = service.clear_user_data(user)
        
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    print(f"Completed. Successfully cleared data for {success_count} users. Failed for {fail_count} users.")
    return success_count > 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear mock Plaid data from Supabase')
    parser.add_argument('--email', help='Email of the specific user to clear data for')
    
    args = parser.parse_args()
    
    if args.email:
        clear_mock_data_for_user(args.email)
    else:
        clear_mock_data_for_all_users() 