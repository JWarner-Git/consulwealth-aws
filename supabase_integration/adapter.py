"""
Adapters for interacting with Supabase database.
These provide domain-specific interfaces for different database needs.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta

from django.conf import settings
from .client import get_supabase_client

logger = logging.getLogger(__name__)

class BaseSupabaseAdapter:
    """
    Base adapter class for Supabase operations.
    Provides the client and common utility methods.
    """
    
    def __init__(self, client=None):
        """Initialize with an optional client for dependency injection"""
        self.client = client or get_supabase_client()
        

class UserAdapter(BaseSupabaseAdapter):
    """
    Adapter for user-related operations in Supabase.
    Handles authentication, profiles, and user management.
    """
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID from Supabase Auth"""
        try:
            response = self.client.auth.admin.get_user_by_id(user_id)
            return response.user
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email from Supabase Auth"""
        try:
            response = self.client.rpc('get_user_by_email', {'email': email}).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def create_user(self, email: str, password: str, user_data: Dict[str, Any] = None) -> Optional[str]:
        """Create a user in Supabase Auth and return the user ID"""
        try:
            # Create user in Supabase Auth
            logger.info(f"Creating auth user with email: {email}")
            response = self.client.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True
            })
            
            user_id = response.user.id
            logger.info(f"Auth user created with ID: {user_id}")
            
            # Initialize a basic profile with default values
            if user_id:
                # Default profile data with values from enum types
                default_profile = {
                    'id': user_id,
                    'email': email,
                    'employment_status': 'employed',  # From employment_status enum
                    'tax_bracket': '0_12',  # From tax_bracket enum
                    'risk_tolerance': 'moderate',  # From risk_level enum
                    'investment_experience': 'beginner',  # From experience_level enum
                    'investment_timeline': 'medium_term',  # From investment_timeline enum
                    'primary_financial_goal': 'retirement',  # From financial_goal enum
                    'secondary_financial_goal': 'emergency'  # From financial_goal enum
                }
                
                # Merge with any user-provided data
                if user_data:
                    default_profile.update(user_data)
                
                # Create the profile
                logger.info(f"Initializing profile for new user {user_id} with data: {default_profile}")
                try:
                    profile_result = self.client.table('profiles').insert(default_profile).execute()
                    
                    if not profile_result.data:
                        logger.error(f"Failed to create profile for user {user_id}: No data returned from insert")
                        # Don't return None here - the auth user was created successfully
                    else:
                        logger.info(f"Profile created successfully: {profile_result.data}")
                except Exception as profile_error:
                    logger.error(f"Exception creating profile for user {user_id}: {str(profile_error)}")
                    logger.error(f"Error details: {repr(profile_error)}")
                    # Continue even if profile creation fails
            
            return user_id
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            logger.error(f"Error details: {repr(e)}")
            return None
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's profile from Supabase"""
        try:
            response = self.client.table('profiles').select('*').eq('id', user_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return None
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's profile with extended information.
        This is an alias for get_profile for API consistency.
        """
        return self.get_profile(user_id)
    
    def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Update a user's profile in Supabase"""
        try:
            # Debugging
            print(f"SupabaseAdapter.update_profile called with user_id: {user_id} (type: {type(user_id)})")
            print(f"Profile data: {profile_data}")
            
            # Ensure id is included in the data and is a string
            if 'id' not in profile_data:
                profile_data['id'] = str(user_id)
                print(f"Added id to profile data: {profile_data['id']}")
            else:
                profile_data['id'] = str(profile_data['id'])
                print(f"Converted existing id to string: {profile_data['id']}")
            
            # Print the SQL that will be used
            table_name = 'profiles'
            print(f"Will execute: UPDATE {table_name} SET ... WHERE id = '{profile_data['id']}'")
            
            # Log the data we're trying to update for debugging
            logger.info(f"Updating profile for user {user_id} with data: {profile_data}")
            
            # Define all valid profile fields based on schema
            valid_fields = [
                'id', 'email', 'phone_number', 'date_of_birth', 'address',
                'employment_status', 'annual_income', 'net_worth', 'tax_bracket',
                'risk_tolerance', 'investment_experience', 'investment_timeline',
                'retirement_age_goal', 'monthly_savings_goal', 
                'primary_financial_goal', 'secondary_financial_goal',
                'target_retirement_savings', 'is_premium_subscriber',
                'subscription_plan', 'subscription_status', 'subscription_end_date'
            ]
            
            # Filter out invalid fields and None values
            clean_data = {}
            for key, value in profile_data.items():
                if key in valid_fields and value is not None:
                    # Convert numeric strings to proper numbers
                    if key in ['annual_income', 'net_worth', 'monthly_savings_goal', 'target_retirement_savings'] and value != '':
                        try:
                            clean_data[key] = float(value)
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert {key}={value} to float, skipping")
                    elif key == 'retirement_age_goal' and value != '':
                        try:
                            clean_data[key] = int(value)
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert {key}={value} to int, skipping")
                    elif key == 'date_of_birth' and value != '':
                        # Ensure date is in ISO format
                        clean_data[key] = value
                    elif key == 'is_premium_subscriber':
                        # Ensure boolean type for this field
                        clean_data[key] = bool(value)
                    elif value != '':  # Skip empty strings
                        clean_data[key] = value
                else:
                    if key not in valid_fields:
                        print(f"Skipping invalid field: {key}")
                    elif value is None:
                        print(f"Skipping null value for field: {key}")
            
            if not clean_data.get('email'):
                # Email is required, get it from existing profile if not provided
                existing_profile = self.get_profile(user_id)
                if existing_profile and existing_profile.get('email'):
                    clean_data['email'] = existing_profile['email']
                    print(f"Added email from existing profile: {clean_data['email']}")
            
            # Debug the cleaned data
            print(f"Cleaned profile data: {clean_data}")
            
            # Make sure the ID is a string, not a number
            if 'id' in clean_data and not isinstance(clean_data['id'], str):
                clean_data['id'] = str(clean_data['id'])
                print(f"Converted ID to string: {clean_data['id']}")
            
            logger.info(f"Sending cleaned profile data to Supabase: {clean_data}")
            
            # Try direct SQL as fallback if regular update fails
            try:
                response = self.client.table('profiles').upsert(clean_data).execute()
                print(f"Supabase profile update response: {response}")
                
                if not response.data:
                    print("No data returned from normal update, trying alternatives...")
                    
                    # Try looking up the profile first to confirm it exists
                    check = self.client.table('profiles').select('*').eq('id', clean_data['id']).execute()
                    if check.data and len(check.data) > 0:
                        print(f"Profile exists in database: {check.data[0]['id']}")
                        # Try update instead of upsert
                        update_resp = self.client.table('profiles').update(clean_data).eq('id', clean_data['id']).execute()
                        print(f"Update response: {update_resp}")
                        if update_resp.data:
                            return True
                    else:
                        print(f"Profile does not exist for ID: {clean_data['id']}")
                        # Try insert instead of upsert
                        insert_resp = self.client.table('profiles').insert(clean_data).execute()
                        print(f"Insert response: {insert_resp}")
                        if insert_resp.data:
                            return True
                    
                    logger.error(f"Empty response when updating profile: {response}")
                    return False
            except Exception as update_error:
                print(f"Error during upsert operation: {str(update_error)}")
                # Try update instead
                try:
                    update_resp = self.client.table('profiles').update(clean_data).eq('id', clean_data['id']).execute()
                    print(f"Fallback update response: {update_resp}")
                    if update_resp.data:
                        return True
                    return False
                except Exception as fallback_error:
                    print(f"Even fallback update failed: {str(fallback_error)}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            logger.error(f"Error details: {repr(e)}")
            print(f"Detailed error in update_profile: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


class FinancialAdapter(BaseSupabaseAdapter):
    """
    Adapter for financial data operations in Supabase.
    Handles goals, accounts, transactions, etc.
    """
    
    def get_financial_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get a user's financial goals from Supabase"""
        try:
            response = self.client.table('financial_goals').select('*').eq('user_id', user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting financial goals: {str(e)}")
            return []
    
    def get_financial_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific financial goal from Supabase"""
        try:
            response = self.client.table('financial_goals').select('*').eq('id', goal_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting financial goal: {str(e)}")
            return None
    
    def create_financial_goal(self, user_id: str, goal_data: Dict[str, Any]) -> Optional[str]:
        """Create a financial goal in Supabase"""
        try:
            # Ensure user_id is included in the data
            goal_data['user_id'] = user_id
            
            # Generate a UUID if not provided
            if 'id' not in goal_data:
                goal_data['id'] = str(uuid.uuid4())
                
            response = self.client.table('financial_goals').insert(goal_data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating financial goal: {str(e)}")
            return None
    
    def update_financial_goal(self, goal_id: str, goal_data: Dict[str, Any]) -> bool:
        """Update a financial goal in Supabase"""
        try:
            # Ensure id is included in the data
            goal_data['id'] = goal_id
            
            response = self.client.table('financial_goals').update(goal_data).eq('id', goal_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating financial goal: {str(e)}")
            return False
    
    def delete_financial_goal(self, goal_id: str) -> bool:
        """Delete a financial goal from Supabase"""
        try:
            response = self.client.table('financial_goals').delete().eq('id', goal_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting financial goal: {str(e)}")
            return False
    
    def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get a user's accounts from Supabase"""
        try:
            response = self.client.table('accounts').select('*').eq('user_id', user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting accounts: {str(e)}")
            return []
    
    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific account from Supabase"""
        try:
            response = self.client.table('accounts').select('*').eq('id', account_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting account: {str(e)}")
            return None
    
    def get_transactions(self, user_id: str, start_date=None, end_date=None, account_id=None) -> List[Dict[str, Any]]:
        """
        Get transactions for a user from Supabase.
        
        Args:
            user_id: The user's ID in Supabase
            start_date: Optional start date filter (YYYY-MM-DD string or date object)
            end_date: Optional end date filter (YYYY-MM-DD string or date object)
            account_id: Optional account ID filter
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # First, get all accounts for this user to know which accounts we need to search for
            accounts_response = self.client.table('accounts').select('id, account_id').eq('user_id', user_id).execute()
            
            if not accounts_response.data:
                logger.info(f"No accounts found for user {user_id}")
                return []
                
            # Extract all account identifiers - both primary key IDs and Plaid account_ids
            account_ids = set()
            for account in accounts_response.data:
                if 'id' in account and account['id']:
                    account_ids.add(account['id'])
                if 'account_id' in account and account['account_id']:
                    account_ids.add(account['account_id'])
            
            logger.info(f"Found {len(account_ids)} account identifiers for user {user_id}")
            
            # Strategy 1: Try to get transactions directly by user_id field
            logger.info(f"Fetching all transactions for user {user_id}...")
            query = self.client.table('transactions').select('*')
            
            # Try different approaches to find transactions
            all_transactions = []
            
            # Approach 1: Use user_id filter to get all user's transactions
            try:
                user_query = self.client.table('transactions').select('*').eq('user_id', user_id)
                
                # Apply date filters if specified
                if start_date and isinstance(start_date, str):
                    user_query = user_query.gte('date', start_date)
                if end_date and isinstance(end_date, str):
                    user_query = user_query.lte('date', end_date)
                
                user_response = user_query.execute()
                if user_response.data:
                    logger.info(f"Found {len(user_response.data)} transactions using user_id filter")
                    all_transactions.extend(user_response.data)
            except Exception as user_error:
                logger.warning(f"Error getting transactions by user_id: {str(user_error)}")
            
            # Approach 2: Get all transactions and filter by account_id
            if not all_transactions:
                try:
                    # Build a query to get all transactions from the database
                    query = self.client.table('transactions').select('*')
                    
                    # Apply date filters if specified
                    if start_date and isinstance(start_date, str):
                        query = query.gte('date', start_date)
                    if end_date and isinstance(end_date, str):
                        query = query.lte('date', end_date)
                    
                    # Execute the query
                    txn_response = query.execute()
                    
                    if txn_response.data:
                        logger.info(f"Found {len(txn_response.data)} transactions in the database")
                        # Filter to only include transactions for this user's accounts
                        for tx in txn_response.data:
                            # Check if this transaction belongs to one of the user's accounts
                            if ('account_id' in tx and tx['account_id'] in account_ids) or \
                               ('user_id' in tx and tx['user_id'] == user_id):
                                all_transactions.append(tx)
                        
                        logger.info(f"After filtering, found {len(all_transactions)} transactions for user {user_id}")
                except Exception as e:
                    logger.warning(f"Error getting all transactions: {str(e)}")
            
            # Apply account_id filter if specified
            if account_id and all_transactions:
                all_transactions = [t for t in all_transactions if 
                                   t.get('account_id') == account_id or 
                                   t.get('account') == account_id]
            
            # Sort by date (newest first)
            all_transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
            logger.info(f"Final count: {len(all_transactions)} transactions for user {user_id}")
            return all_transactions
                
        except Exception as e:
            logger.error(f"Error getting transactions: {str(e)}")
            logger.exception("Full traceback:")
            return []


class PlaidAdapter(BaseSupabaseAdapter):
    """
    Adapter for Plaid-related operations in Supabase.
    Handles Plaid items, accounts, and transactions.
    """
    
    def store_plaid_item(self, user_id: str, item_id: str, access_token: str, institution_id: str = None, 
                        institution_name: str = None, institution_logo: str = None) -> Optional[str]:
        """Store a Plaid item in Supabase"""
        try:
            # Create the basic item data with required fields
            item_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'item_id': item_id,
                'access_token': access_token
            }
            
            # Add institution_id if provided - but don't try to use it as a UUID
            # Store it as a regular string field instead
            if institution_id:
                item_data['institution_id'] = institution_id
                
            # Add institution_name if provided
            if institution_name:
                item_data['institution_name'] = institution_name
                
            # Add institution_logo if provided
            if institution_logo:
                item_data['institution_logo'] = institution_logo
            
            # Try to add the enhanced fields, but don't fail if they don't exist
            try:
                now = datetime.now(timezone.utc).isoformat()
                next_refresh = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
                
                # Enhanced fields for refresh strategy
                enhanced_data = {
                    'last_successful_update': now,
                    'last_connection_time': now,
                    'connection_status': 'active',
                    'update_type': 'initial',
                    'next_hard_refresh': next_refresh
                }
                
                # Try storing with all fields
                try:
                    item_data.update(enhanced_data)
                    response = self.client.table('plaid_items').insert(item_data).execute()
                    if response.data and len(response.data) > 0:
                        logger.info(f"Successfully stored Plaid item with enhanced fields: {item_id}")
                        return response.data[0]['id']
                except Exception as full_error:
                    # If it failed, try again with just the required fields
                    logger.warning(f"Failed to store Plaid item with enhanced fields, trying with basic fields: {str(full_error)}")
                    
                    # Reset item_data to just the basic fields
                    item_data = {
                        'id': str(uuid.uuid4()),
                        'user_id': user_id,
                        'item_id': item_id,
                        'access_token': access_token
                    }
                    if institution_id:
                        item_data['institution_id'] = institution_id
                    
                    response = self.client.table('plaid_items').insert(item_data).execute()
                    if response.data and len(response.data) > 0:
                        logger.info(f"Successfully stored Plaid item with basic fields: {item_id}")
                        return response.data[0]['id']
                    return None
            except Exception as enhanced_error:
                # If adding enhanced fields fails, try with just the basic data
                logger.warning(f"Could not add enhanced fields to Plaid item, using basic fields: {str(enhanced_error)}")
                response = self.client.table('plaid_items').insert(item_data).execute()
                if response.data and len(response.data) > 0:
                    logger.info(f"Successfully stored Plaid item with basic fields after enhanced field error: {item_id}")
                    return response.data[0]['id']
            
            return None
        except Exception as e:
            logger.error(f"Error storing Plaid item: {str(e)}")
            return None
    
    def get_plaid_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all Plaid items for a user from Supabase"""
        try:
            response = self.client.table('plaid_items').select('*').eq('user_id', user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting Plaid items: {str(e)}")
            return []
    
    def get_plaid_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific Plaid item by its ID or item_id"""
        try:
            # First try to find by id (the UUID primary key in our table)
            logger.debug(f"Attempting to find Plaid item with id={item_id}")
            response = self.client.table('plaid_items').select('*').eq('id', item_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.debug(f"Found Plaid item by id (primary key)")
                return response.data[0]
                
            # If not found, try finding by item_id (Plaid's item_id) 
            logger.debug(f"Item not found by id, trying item_id={item_id}")
            response = self.client.table('plaid_items').select('*').eq('item_id', item_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.debug(f"Found Plaid item by item_id (Plaid's ID)")
                return response.data[0]
                
            logger.warning(f"Plaid item not found with id or item_id = {item_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting Plaid item by ID: {str(e)}")
            return None
    
    def store_account(self, user_id=None, account_data=None):
        """Store account data in the database
        
        Args:
            user_id (str): The user ID to associate the account with
            account_data (dict): Account data
            
        Returns:
            dict: The stored account data
        """
        try:
            # Ensure we have both required parameters
            if account_data is None:
                logger.error("Missing account_data parameter")
                return None
            
            # Check if user_id was provided as a parameter
            if user_id:
                # Ensure user_id is set in the account data
                account_data['user_id'] = user_id
            
            # As a fallback, check if account_data already contains user_id
            if 'user_id' not in account_data or not account_data['user_id']:
                logger.error("Missing user_id in account data")
                return None
            
            # Start with the lookup strategy
            is_update = False
            account_id = None
            
            # If we already have an ID, this is an update of an existing account
            if 'id' in account_data and account_data['id']:
                is_update = True
                account_id = account_data['id']
                logger.info(f"Updating account by ID: {account_id}")
                
                # Verify the account exists and belongs to this user
                try:
                    check_resp = self.client.table('accounts').select('id').eq('id', account_id).eq('user_id', user_id).execute()
                    if not check_resp.data or not check_resp.data[0]:
                        logger.warning(f"Account ID {account_id} not found for user {user_id}, will treat as new account instead")
                        is_update = False
                        del account_data['id']  # Remove the ID to ensure we insert a new record
                except Exception as check_err:
                    logger.error(f"Error verifying account: {str(check_err)}")
                    is_update = False
                    del account_data['id']
            
            # Otherwise check if account already exists by Plaid account_id
            if not is_update:
                plaid_account_id = account_data.get('account_id')
                
                if not plaid_account_id:
                    logger.error("Missing account_id in account data")
                    return None
                
                # Look for existing account by plaid account_id
                try:
                    response = self.client.table('accounts').select('*').eq('account_id', plaid_account_id).eq('user_id', user_id).execute()
                    
                    if response.data and len(response.data) > 0:
                        is_update = True
                        account_id = response.data[0]['id']
                        logger.info(f"Found existing account by account_id {plaid_account_id}, will update: {account_id}")
                except Exception as find_err:
                    logger.error(f"Error looking up account: {str(find_err)}")
            
            # Now perform the operation (update or insert)
            if is_update:
                # Update existing account
                
                # Don't update user_id
                update_data = {k: v for k, v in account_data.items() if k != 'user_id'}
                
                # Include a last_updated timestamp
                update_data['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                try:
                    self.client.table('accounts').update(update_data).eq('id', account_id).execute()
                    
                    # Get the updated account
                    updated = self.client.table('accounts').select('*').eq('id', account_id).execute()
                    if updated.data and len(updated.data) > 0:
                        return updated.data[0]
                    return None
                except Exception as update_err:
                    logger.error(f"Error updating account {account_id}: {str(update_err)}")
                    return None
            else:
                # Insert new account
                # Add a created timestamp
                account_data['created_at'] = datetime.now(timezone.utc).isoformat()
                account_data['last_updated'] = account_data['created_at']
                
                try:
                    response = self.client.table('accounts').insert(account_data).execute()
                    
                    if response.data and len(response.data) > 0:
                        logger.info(f"Created new account: {response.data[0]['id']} - {account_data.get('name')}")
                        return response.data[0]
                    return None
                except Exception as insert_err:
                    logger.error(f"Error inserting new account: {str(insert_err)}")
                    return None
                
        except Exception as e:
            logger.error(f"Error storing account data: {str(e)}")
            return None
    
    def _clean_account_data(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean account data to prevent schema issues"""
        try:
            # Create a copy to avoid modifying the original
            clean_data = {}
            
            # Base fields that must be in the database for the account to work
            essential_fields = ['id', 'user_id', 'account_id', 'name', 'current_balance', 'available_balance']
            
            # Get the full list of all possible fields from the account_data
            all_fields = list(account_data.keys())
            
            # Check and copy essential fields first
            for field in essential_fields:
                if field in account_data:
                    clean_data[field] = account_data[field]
            
            # Handle institution_id - ensure it's stored as text
            if 'institution_id' in account_data:
                # Keep it as a string, don't try to convert to UUID
                if account_data['institution_id'] is not None:
                    clean_data['institution_id'] = account_data['institution_id']
            
            # Handle Plaid item_id - ensure it's stored as text
            if 'plaid_item_id' in account_data:
                if account_data['plaid_item_id'] is not None:
                    clean_data['plaid_item_id'] = str(account_data['plaid_item_id'])
            
            # Map fields to match database schema - this is critically important
            field_mapping = {
                'account_type': 'type',  # Database uses 'type' not 'account_type'
                'is_auth': 'is_authenticated',  # Map for consistency
            }
            
            # Try to check the actual table schema to see what columns exist
            try:
                schema_columns = []
                try:
                    # Get columns from the schema cache (only works with newer Supabase)
                    response = self.client.table('accounts').select('*').limit(1).execute()
                    if response and hasattr(response, 'data') and response.data:
                        schema_columns = list(response.data[0].keys())
                    logger.debug(f"Retrieved schema columns from Supabase: {schema_columns}")
                except Exception as schema_error:
                    logger.warning(f"Could not get schema columns: {str(schema_error)}")
                
                # Now check if mapped fields exist in the schema
                for old_field, new_field in field_mapping.items():
                    if old_field in account_data:
                        # Only map if the new field exists in schema
                        if not schema_columns or new_field in schema_columns:
                            clean_data[new_field] = account_data[old_field]
                        # If new field doesn't exist but old does, use old field as fallback
                        elif not schema_columns or old_field in schema_columns:
                            clean_data[old_field] = account_data[old_field]
            except Exception as mapping_error:
                logger.warning(f"Error with field mapping: {str(mapping_error)}")
                # Default behavior if schema check fails - just do the mapping
                for old_field, new_field in field_mapping.items():
                    if old_field in account_data:
                        clean_data[new_field] = account_data[old_field]
            
            # Copy all remaining fields safely
            for field in all_fields:
                # Skip fields we've already handled
                if field in essential_fields or field in field_mapping or field == 'institution_id' or field == 'plaid_item_id':
                    continue
                    
                # Handle special cases for investment and auth flags
                if field == 'is_investment' or field == 'is_investment_account':
                    # Ensure both flags are set if either is True
                    is_investment = account_data.get('is_investment', False)
                    is_investment_account = account_data.get('is_investment_account', False)
                    
                    if is_investment or is_investment_account:
                        clean_data['is_investment'] = True
                        clean_data['is_investment_account'] = True
                elif field == 'subtype' or field == 'account_subtype':
                    # Handle subtype/account_subtype consistently
                    subtype = account_data.get('subtype')
                    account_subtype = account_data.get('account_subtype')
                    
                    # Prefer subtype if both exist
                    if subtype:
                        clean_data['subtype'] = subtype
                    elif account_subtype:
                        clean_data['subtype'] = account_subtype
                else:
                    # For all other fields, copy them directly
                    if account_data[field] is not None:
                        clean_data[field] = account_data[field]
            
            # Ensure numeric fields are actual numbers
            numeric_fields = ['current_balance', 'available_balance', 'interest_rate', 
                             'late_fee', 'minimum_payment', 'available_credit', 
                             'credit_limit', 'loan_balance', 'payment_amount',
                             'portfolio_value']
            
            for field in numeric_fields:
                if field in clean_data:
                    try:
                        if clean_data[field] is not None:
                            clean_data[field] = float(clean_data[field])
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert {field} to number, setting to 0")
                        clean_data[field] = 0
            
            # Log what we're actually storing
            logger.debug(f"Cleaned account data, keeping fields: {list(clean_data.keys())}")
            
            return clean_data
        except Exception as e:
            logger.error(f"Error in _clean_account_data: {str(e)}")
            # Return the original data as a fallback
            return account_data
    
    def store_security(self, security_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a security record in Supabase.
        
        Args:
            security_data: Security data from Plaid
            
        Returns:
            The Supabase security ID if successful, None otherwise
        """
        try:
            security_id = security_data.get('security_id')
            
            if not security_id:
                logger.warning("No security_id provided in security data")
                return None
            
            # For logging purposes, get the ticker or security_id if name is missing
            log_identifier = security_data.get('name') or security_data.get('ticker_symbol') or security_id
                
            # Check if security already exists
            existing = self.client.table('securities').select('id').eq('security_id', security_id).execute()
                
            # Prepare data for storage
            security_record = {
                'security_id': security_id,
                # Ensure name is never null - default to security_id or "Unknown Security"
                'name': security_data.get('name') or f"Unknown Security ({security_data.get('ticker_symbol') or security_id})",
                'ticker_symbol': security_data.get('ticker_symbol'),
                'isin': security_data.get('isin'),
                'cusip': security_data.get('cusip'),
                'type': security_data.get('type'),
                'close_price': security_data.get('close_price'),
                'currency_code': security_data.get('iso_currency_code', 'USD')
            }
            
            # Handle close_price_as_of date
            close_price_as_of = security_data.get('close_price_as_of')
            if close_price_as_of:
                if isinstance(close_price_as_of, datetime):
                    security_record['close_price_as_of'] = close_price_as_of.isoformat()
                elif hasattr(close_price_as_of, 'isoformat'):
                    security_record['close_price_as_of'] = close_price_as_of.isoformat()
                else:
                    security_record['close_price_as_of'] = str(close_price_as_of)
            
            # Add current timestamp for created_at and updated_at if not already set
            if 'created_at' not in security_record:
                security_record['created_at'] = datetime.now(timezone.utc).isoformat()
                
            if 'updated_at' not in security_record:
                security_record['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # If id exists in the data, include it (for data migration)
            if 'id' in security_data:
                security_record['id'] = security_data['id']
            
            # Create or update security
            if existing.data and len(existing.data) > 0:
                # Update existing security
                security_db_id = existing.data[0]['id']
                response = self.client.table('securities').update(security_record).eq('id', security_db_id).execute()
                logger.info(f"Updated existing security: {log_identifier}")
            else:
                # Create new security with a UUID if not provided
                if 'id' not in security_record:
                    security_record['id'] = str(uuid.uuid4())
                response = self.client.table('securities').insert(security_record).execute()
                logger.info(f"Created new security: {log_identifier}")
                
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
                
            logger.warning(f"No data returned when storing security: {response}")
            return None
        except Exception as e:
            logger.error(f"Error storing security: {str(e)}")
            return None
            
    def store_holding(self, account_id: str, security_id: str, holding_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a holding record in Supabase.
        
        Args:
            account_id: The account ID
            security_id: The security ID
            holding_data: Holding data from Plaid
            
        Returns:
            The Supabase holding ID if successful, None otherwise
        """
        try:
            # Check for existing holding with this account/security combination
            existing = self.client.table('account_holdings') \
                .select('id') \
                .eq('account_id', account_id) \
                .eq('security_id', security_id) \
                .execute()
                
            # Prepare data for storage
            holding_record = {
                'account_id': account_id,
                'security_id': security_id,
                'cost_basis': holding_data.get('cost_basis'),
                'quantity': holding_data.get('quantity', 0),
                'institution_value': holding_data.get('institution_value'),
                'institution_price': holding_data.get('institution_price')
            }
            
            # Handle date objects by converting to ISO format strings
            price_as_of = holding_data.get('institution_price_as_of')
            if price_as_of:
                if isinstance(price_as_of, datetime):
                    holding_record['institution_price_as_of'] = price_as_of.isoformat()
                elif hasattr(price_as_of, 'isoformat'):
                    holding_record['institution_price_as_of'] = price_as_of.isoformat()
                else:
                    holding_record['institution_price_as_of'] = str(price_as_of)
            
            # Similarly handle any other potential date fields
            for date_field in ['purchase_date', 'updated_at']:
                if date_field in holding_data:
                    date_value = holding_data.get(date_field)
                    if date_value:
                        if isinstance(date_value, datetime):
                            holding_record[date_field] = date_value.isoformat()
                        elif hasattr(date_value, 'isoformat'):
                            holding_record[date_field] = date_value.isoformat()
                        else:
                            holding_record[date_field] = str(date_value)
            
            # Add current timestamp for updated_at if not provided
            if 'updated_at' not in holding_record:
                holding_record['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Create or update holding
            if existing.data and len(existing.data) > 0:
                # Update existing holding
                holding_db_id = existing.data[0]['id']
                response = self.client.table('account_holdings') \
                    .update(holding_record) \
                    .eq('id', holding_db_id) \
                    .execute()
                logger.info(f"Updated existing holding for account {account_id}, security {security_id}")
            else:
                # Create new holding with a UUID
                holding_record['id'] = str(uuid.uuid4())
                response = self.client.table('account_holdings') \
                    .insert(holding_record) \
                    .execute()
                logger.info(f"Created new holding for account {account_id}, security {security_id}")
                    
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
                
            logger.warning(f"No data returned when storing holding: {response}")
            return None
        except Exception as e:
            logger.error(f"Error storing holding: {str(e)}")
            return None
    
    def get_holdings(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all holdings for a user from Supabase.
        
        Args:
            user_id: The user ID
            
        Returns:
            A list of holdings
        """
        try:
            # First get all accounts for the user directly from the database
            # Instead of calling get_accounts which doesn't exist in this class
            accounts_response = self.client.table('accounts').select('id').eq('user_id', user_id).execute()
            if not accounts_response.data:
                return []
            
            # Get account IDs
            account_ids = [account['id'] for account in accounts_response.data]
            
            # Get holdings for these accounts
            all_holdings = []
            
            # Query each account separately and combine results
            for account_id in account_ids:
                try:
                    response = self.client.table('account_holdings').select('*').eq('account_id', account_id).execute()
                    if response.data:
                        all_holdings.extend(response.data)
                except Exception as e:
                    logger.warning(f"Error fetching holdings for account {account_id}: {str(e)}")
            
            return all_holdings
        except Exception as e:
            logger.error(f"Error getting holdings: {str(e)}")
            return []
    
    def get_securities(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get securities related to a user's holdings from Supabase.
        
        Args:
            user_id: The user ID
            
        Returns:
            A list of securities
        """
        try:
            # First get all accounts for the user directly from the database
            accounts_response = self.client.table('accounts').select('id').eq('user_id', user_id).execute()
            if not accounts_response.data:
                return []
            
            account_ids = [account['id'] for account in accounts_response.data]
            
            # Get all holdings for these accounts
            all_holdings = []
            for account_id in account_ids:
                try:
                    holdings_response = self.client.table('account_holdings').select('security_id').eq('account_id', account_id).execute()
                    if holdings_response.data:
                        all_holdings.extend(holdings_response.data)
                except Exception as e:
                    logger.warning(f"Error fetching holdings for account {account_id}: {str(e)}")
            
            if not all_holdings:
                return []
            
            # Extract unique security IDs
            security_ids = list(set(holding.get('security_id') for holding in all_holdings 
                                  if holding.get('security_id')))
            
            if not security_ids:
                return []
            
            # Get securities for these security IDs
            all_securities = []
            
            # Query each security separately to avoid issues with .in_() operation
            for security_id in security_ids:
                try:
                    response = self.client.table('securities').select('*').eq('id', security_id).execute()
                    if response.data and len(response.data) > 0:
                        all_securities.append(response.data[0])
                except Exception as e:
                    logger.warning(f"Error fetching security {security_id}: {str(e)}")
            
            return all_securities
        except Exception as e:
            logger.error(f"Error getting securities: {str(e)}")
            return []
    
    def store_transactions(self, transactions: List[Dict[str, Any]]) -> bool:
        """Store multiple transactions in Supabase"""
        try:
            # Prepare transactions for insertion, filtering out fields that might not exist in schema
            logger.info(f"Preparing {len(transactions)} transactions for storage")
            
            from .utils import serialize_for_supabase, clean_for_schema, extract_schema_columns
            
            # Get the known schema columns for transactions table
            try:
                # Try to query with limit 0 to get column info without fetching data
                response = self.client.table('transactions').select('*').limit(0).execute()
                # Extract schema columns using our utility
                schema_columns = extract_schema_columns(response)
                
                if not schema_columns:
                    # Fallback to a list of known safe columns
                    schema_columns = [
                        'id', 'account_id', 'transaction_id', 'amount', 'date', 'name',
                        'merchant_name', 'category', 'pending', 'reference_number', 'payee',
                        'user_id', 'location', 'payment_channel', 'payment_method', 'payer',
                        'category_id', 'subcategory', 'authorized_date', 'iso_currency_code',
                        'unofficial_currency_code', 'website', 'account_name', 'account_owner',
                        'description'
                    ]
                    logger.warning(f"Could not determine schema columns, using safe defaults: {schema_columns}")
            except Exception as schema_error:
                # If we can't get schema, use safe defaults
                schema_columns = [
                    'id', 'account_id', 'transaction_id', 'amount', 'date', 'name',
                    'merchant_name', 'category', 'pending', 'reference_number', 'payee',
                    'user_id', 'location', 'payment_channel', 'payment_method', 'payer',
                    'category_id', 'subcategory', 'authorized_date', 'iso_currency_code',
                    'unofficial_currency_code', 'website', 'account_name', 'account_owner',
                    'description'
                ]
                logger.warning(f"Error getting schema: {str(schema_error)}. Using safe defaults: {schema_columns}")
            
            # For each transaction, fetch the related account and add the user_id to the transaction
            # This ensures transactions can be properly filtered by user later
            user_id_map = {}  # Cache for account_id to user_id mapping
            
            # Filter transactions to only include fields in the schema and ensure all values are serialized
            filtered_transactions = []
            for tx in transactions:
                # Ensure required fields are present
                if 'id' not in tx:
                    tx['id'] = str(uuid.uuid4())
                
                # Try to add user_id to transaction if missing
                if 'user_id' not in tx and 'account_id' in tx:
                    account_id = tx['account_id']
                    
                    # Check the cache first
                    if account_id in user_id_map:
                        tx['user_id'] = user_id_map[account_id]
                    else:
                        # Look up the account to get its user_id
                        try:
                            account_response = self.client.table('accounts').select('user_id').eq('account_id', account_id).execute()
                            if account_response.data and len(account_response.data) > 0 and 'user_id' in account_response.data[0]:
                                user_id = account_response.data[0]['user_id']
                                user_id_map[account_id] = user_id  # Cache for future use
                                tx['user_id'] = user_id
                            else:
                                # Try looking up by other methods if initial lookup fails
                                # 1. Try using UUID format of account_id
                                try:
                                    account_response = self.client.table('accounts').select('user_id').eq('id', account_id).execute()
                                    if account_response.data and len(account_response.data) > 0 and 'user_id' in account_response.data[0]:
                                        user_id = account_response.data[0]['user_id']
                                        user_id_map[account_id] = user_id  # Cache for future use
                                        tx['user_id'] = user_id
                                except Exception as uuid_error:
                                    # Handle silently, this is just an alternative approach
                                    pass
                        except Exception as account_error:
                            logger.warning(f"Could not get user_id for account {account_id}: {str(account_error)}")
                
                # Clean and serialize transaction data
                filtered_tx = clean_for_schema(tx, schema_columns)
                filtered_transactions.append(filtered_tx)
            
            logger.info(f"Filtered transactions to match schema, prepared {len(filtered_transactions)} for insertion")
            
            # Insert in batches of 100 to avoid payload size limits
            batch_size = 100
            successful_batches = 0
            for i in range(0, len(filtered_transactions), batch_size):
                batch = filtered_transactions[i:i+batch_size]
                
                try:
                    response = self.client.table('transactions').insert(batch).execute()
                    if response.data:
                        successful_batches += 1
                        logger.info(f"Successfully inserted batch {successful_batches} ({len(batch)} transactions)")
                    else:
                        logger.error(f"Error inserting batch {i//batch_size + 1}: No data returned")
                        return False
                except Exception as batch_error:
                    logger.error(f"Error inserting batch {i//batch_size + 1}: {str(batch_error)}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error storing transactions: {str(e)}")
            return False
    
    def update_plaid_item_status(self, item_id: str, status: str = None, 
                           update_type: str = None, last_update: str = None, 
                           next_hard_refresh: str = None) -> bool:
        """Update the status of a Plaid item in the database"""
        try:
            # Start with the basic update data
            update_data = {}
            
            # Only add fields if they are provided and try to update incrementally
            if status:
                try:
                    # Try to update just the status
                    status_data = {'connection_status': status}
                    status_response = self.client.table('plaid_items').update(status_data).eq('item_id', item_id).execute()
                    if status_response.data:
                        update_data.update(status_data)  # Track that we successfully updated
                except Exception as status_error:
                    logger.warning(f"Failed to update connection_status: {str(status_error)}")
            
            if update_type:
                try:
                    # Try to update just the update_type
                    update_type_data = {'update_type': update_type}
                    type_response = self.client.table('plaid_items').update(update_type_data).eq('item_id', item_id).execute()
                    if type_response.data:
                        update_data.update(update_type_data)  # Track that we successfully updated
                except Exception as type_error:
                    logger.warning(f"Failed to update update_type: {str(type_error)}")
            
            if last_update:
                try:
                    # Try to update just the last_successful_update
                    last_update_data = {'last_successful_update': last_update}
                    last_update_response = self.client.table('plaid_items').update(last_update_data).eq('item_id', item_id).execute()
                    if last_update_response.data:
                        update_data.update(last_update_data)  # Track that we successfully updated
                except Exception as last_update_error:
                    logger.warning(f"Failed to update last_successful_update: {str(last_update_error)}")
            
            if next_hard_refresh:
                try:
                    # Try to update just the next_hard_refresh
                    next_refresh_data = {'next_hard_refresh': next_hard_refresh}
                    refresh_response = self.client.table('plaid_items').update(next_refresh_data).eq('item_id', item_id).execute()
                    if refresh_response.data:
                        update_data.update(next_refresh_data)  # Track that we successfully updated
                except Exception as refresh_error:
                    logger.warning(f"Failed to update next_hard_refresh: {str(refresh_error)}")
            
            # Return success if we updated at least one field
            return len(update_data) > 0
        
        except Exception as e:
            logger.error(f"Error updating Plaid item status: {str(e)}")
            return False
            
    def record_soft_refresh(self, item_id: str) -> bool:
        """Record a soft refresh of a Plaid item"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            return self.update_plaid_item_status(
                item_id=item_id,
                status='active',
                update_type='soft',
                last_update=now
            )
        except Exception as e:
            logger.error(f"Error recording soft refresh: {str(e)}")
            return False
            
    def record_hard_refresh(self, item_id: str) -> bool:
        """Record a hard refresh of a Plaid item"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            next_refresh = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
            return self.update_plaid_item_status(
                item_id=item_id,
                status='active',
                update_type='hard',
                last_update=now,
                next_hard_refresh=next_refresh
            )
        except Exception as e:
            logger.error(f"Error recording hard refresh: {str(e)}")
            return False
            
    def get_items_needing_refresh(self, user_id: str = None, refresh_type: str = 'soft') -> List[Dict[str, Any]]:
        """Get Plaid items that need refresh based on type and schedule"""
        try:
            query = self.client.table('plaid_items').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
                
            try:
                if refresh_type == 'hard':
                    # Items needing hard refresh (quarterly)
                    try:
                        # Try to fetch using next_hard_refresh field
                        query = query.lt('next_hard_refresh', datetime.now(timezone.utc).isoformat())
                    except Exception as column_error:
                        logger.warning(f"Could not query on next_hard_refresh column, returning empty list: {str(column_error)}")
                        return []
                else:
                    # Items needing soft refresh (weekly)
                    # Consider items last updated more than 7 days ago
                    try:
                        # Try to fetch using last_successful_update field
                        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                        query = query.lt('last_successful_update', seven_days_ago)
                    except Exception as column_error:
                        logger.warning(f"Could not query on last_successful_update column, returning empty list: {str(column_error)}")
                        return []
                
                response = query.execute()
                return response.data or []
            except Exception as query_error:
                logger.error(f"Error constructing refresh query: {str(query_error)}")
                # Return empty list to prevent cascading errors
                return []
                
        except Exception as e:
            logger.error(f"Error getting items needing refresh: {str(e)}")
            return []
            
    def get_connected_institutions(self, user_id: str) -> List[str]:
        """Get list of institution IDs connected by the user"""
        try:
            response = self.client.table('plaid_items').select('institution_id').eq('user_id', user_id).execute()
            if response.data:
                return [item.get('institution_id') for item in response.data if item.get('institution_id')]
            return []
        except Exception as e:
            logger.error(f"Error getting connected institutions: {str(e)}")
            return []
    
    def get_security_by_plaid_id(self, plaid_security_id):
        """Get a security by its Plaid ID"""
        try:
            response = self.client.table('securities').select('*').eq('plaid_security_id', plaid_security_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting security by Plaid ID: {str(e)}")
            return None
    
    def create_security(self, security_data):
        """Create a new security"""
        try:
            response = self.client.table('securities').insert(security_data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating security: {str(e)}")
            return None
    
    def update_security(self, security_id, security_data):
        """Update a security"""
        try:
            # Filter out None values
            security_update = {k: v for k, v in security_data.items() if v is not None}
            
            # Convert to the expected format
            mapped_data = {
                'name': security_update.get('name'),
                'ticker_symbol': security_update.get('ticker_symbol'),
                'type': security_update.get('type'),
                'close_price': security_update.get('close_price'),
                'close_price_as_of': security_update.get('close_price_as_of'),
                'iso_currency_code': security_update.get('iso_currency_code'),
            }
            
            # Filter out None values again
            mapped_data = {k: v for k, v in mapped_data.items() if v is not None}
            
            response = self.client.table('securities').update(mapped_data).eq('id', security_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating security: {str(e)}")
            return False
    
    def get_holding_by_account_and_security(self, account_id, security_id):
        """Get a holding by account ID and security ID"""
        try:
            response = self.client.table('account_holdings') \
                .select('*') \
                .eq('account_id', account_id) \
                .eq('security_id', security_id) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting holding by account and security: {str(e)}")
            return None
    
    def create_holding(self, holding_data):
        """Create a new holding"""
        try:
            response = self.client.table('account_holdings').insert(holding_data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating holding: {str(e)}")
            return None
    
    def update_holding(self, holding_id, holding_data):
        """Update a holding"""
        try:
            # Filter out None values
            holding_update = {k: v for k, v in holding_data.items() if v is not None}
            
            response = self.client.table('account_holdings').update(holding_update).eq('id', holding_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating holding: {str(e)}")
            return False
    
    def get_account_by_plaid_id(self, plaid_account_id):
        """Get an account by its Plaid ID"""
        try:
            if not plaid_account_id:
                logger.error("Cannot get account with empty plaid_account_id")
                return None
                
            # Query the accounts table for this Plaid account_id
            response = self.client.table('accounts').select('*').eq('account_id', plaid_account_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            logger.warning(f"No account found with Plaid account_id {plaid_account_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting account by Plaid ID: {str(e)}")
            return None
    
    def update_plaid_item(self, plaid_item_id, item_data):
        """Update a Plaid item with additional data"""
        try:
            # Filter out None values
            item_update = {k: v for k, v in item_data.items() if v is not None}
            
            response = self.client.table('plaid_items').update(item_update).eq('id', plaid_item_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating Plaid item: {str(e)}")
            return False

# Legacy adapter for backward compatibility
class SupabaseAdapter:
    """
    Legacy adapter that delegates to domain-specific adapters.
    This is for backward compatibility and should be phased out.
    """
    
    def __init__(self, client=None):
        self.client = client or get_supabase_client()
        self.user_adapter = UserAdapter(self.client)
        self.financial_adapter = FinancialAdapter(self.client)
        self.plaid_adapter = PlaidAdapter(self.client)
    
    # Delegate user methods
    def get_user_by_id(self, user_id: str):
        return self.user_adapter.get_user_by_id(user_id)
        
    def get_user_by_email(self, email: str):
        return self.user_adapter.get_user_by_email(email)
        
    def create_user(self, email: str, password: str, user_data=None):
        return self.user_adapter.create_user(email, password, user_data)
        
    def get_profile(self, user_id: str):
        return self.user_adapter.get_profile(user_id)
    
    def get_user_profile(self, user_id: str):
        return self.user_adapter.get_user_profile(user_id)
        
    def update_profile(self, user_id: str, profile_data):
        return self.user_adapter.update_profile(user_id, profile_data)
    
    # Delegate financial methods
    def get_financial_goals(self, user_id: str):
        return self.financial_adapter.get_financial_goals(user_id)
        
    def get_financial_goal(self, goal_id: str):
        return self.financial_adapter.get_financial_goal(goal_id)
        
    def create_financial_goal(self, user_id: str, goal_data):
        return self.financial_adapter.create_financial_goal(user_id, goal_data)
        
    def update_financial_goal(self, goal_id: str, goal_data):
        return self.financial_adapter.update_financial_goal(goal_id, goal_data)
        
    def delete_financial_goal(self, goal_id: str):
        return self.financial_adapter.delete_financial_goal(goal_id)
        
    def get_accounts(self, user_id: str):
        return self.financial_adapter.get_accounts(user_id)
        
    def get_account(self, account_id: str):
        return self.financial_adapter.get_account(account_id)
        
    def get_transactions(self, user_id: str, start_date=None, end_date=None, account_id=None):
        return self.financial_adapter.get_transactions(user_id, start_date, end_date, account_id)
    
    # Delegate plaid methods
    def store_plaid_item(self, user_id: str, item_id: str, access_token: str, institution_id: str = None, 
                        institution_name: str = None, institution_logo: str = None):
        return self.plaid_adapter.store_plaid_item(user_id, item_id, access_token, institution_id, institution_name, institution_logo)
        
    def get_plaid_items(self, user_id: str):
        return self.plaid_adapter.get_plaid_items(user_id)
        
    def get_plaid_item_by_id(self, item_id: str):
        return self.plaid_adapter.get_plaid_item_by_id(item_id)
        
    def store_account(self, user_id=None, account_data=None):
        return self.plaid_adapter.store_account(user_id, account_data)
        
    def store_transactions(self, transactions):
        return self.plaid_adapter.store_transactions(transactions)
        
    def update_plaid_item_status(self, item_id: str, status: str = None, 
                           update_type: str = None, last_update: str = None, 
                           next_hard_refresh: str = None):
        return self.plaid_adapter.update_plaid_item_status(item_id, status, update_type, last_update, next_hard_refresh)
        
    def record_soft_refresh(self, item_id: str):
        return self.plaid_adapter.record_soft_refresh(item_id)
        
    def record_hard_refresh(self, item_id: str):
        return self.plaid_adapter.record_hard_refresh(item_id)
        
    def get_items_needing_refresh(self, user_id: str = None, refresh_type: str = 'soft'):
        return self.plaid_adapter.get_items_needing_refresh(user_id, refresh_type)
        
    def get_connected_institutions(self, user_id: str):
        return self.plaid_adapter.get_connected_institutions(user_id)
        
    # Add missing methods for securities and holdings
    def get_securities(self, user_id: str):
        return self.plaid_adapter.get_securities(user_id)
        
    def get_holdings(self, user_id: str):
        return self.plaid_adapter.get_holdings(user_id)
        
    def store_security(self, security_data):
        return self.plaid_adapter.store_security(security_data)
        
    def store_holding(self, account_id, security_id, holding_data):
        return self.plaid_adapter.store_holding(account_id, security_id, holding_data)
    
    def get_account_by_plaid_id(self, plaid_account_id):
        """Get an account by its Plaid ID"""
        return self.plaid_adapter.get_account_by_plaid_id(plaid_account_id)

    def verify_jwt_token(self, token):
        """
        Verify a JWT token from a mobile client and return the user.
        
        Args:
            token (str): The JWT token to verify
            
        Returns:
            User: The user object if verification succeeds
            
        Raises:
            ValueError: If verification fails
        """
        try:
            # Get the user information from the token
            response = self.client.auth.get_user(token)
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error verifying JWT token: {response.error.message}")
                raise ValueError(f"Invalid token: {response.error.message}")
            
            if not response.user:
                logger.error("No user found in token response")
                raise ValueError("Invalid token: No user found")
            
            # Check if the user exists in our database
            user_id = response.user.id
            user = self.get_user_by_id(user_id)
            
            if not user:
                logger.error(f"User with ID {user_id} not found in database")
                raise ValueError("User not found")
                
            return user
        except Exception as e:
            logger.error(f"Error verifying JWT token: {str(e)}")
            raise ValueError(f"Token verification failed: {str(e)}")

    def get_user_by_id(self, user_id):
        """
        Get a user by their ID.
        
        Args:
            user_id (str): The Supabase user ID
            
        Returns:
            User: The user object if found, None otherwise
        """
        try:
            # Query the users table for the user
            user_data = self.client.table('users').select('*').eq('id', user_id).execute()
            
            if not user_data.data:
                # Try the profiles table as a fallback
                profile_data = self.client.table('profiles').select('*').eq('id', user_id).execute()
                
                if not profile_data.data:
                    logger.warning(f"User with ID {user_id} not found")
                    return None
                    
                # Create a user object from the profile data
                user_info = profile_data.data[0]
            else:
                user_info = user_data.data[0]
            
            # Create a user-like object with the required attributes
            # This is a simplified approach - in production you might want
            # to create a proper User object that mimics Django's User
            class SupabaseUser:
                def __init__(self, user_data):
                    self.id = user_data.get('id')
                    self.email = user_data.get('email')
                    self.is_authenticated = True
                    
                    # Add any other fields you need from the user data
                    for key, value in user_data.items():
                        setattr(self, key, value)
            
            return SupabaseUser(user_info)
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None 