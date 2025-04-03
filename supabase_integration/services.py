from django.conf import settings
from .client import SupabaseClient, get_supabase_client
from typing import Dict, Any, Optional, List
import logging
import uuid
import random
import string
from .adapter import SupabaseAdapter, UserAdapter, FinancialAdapter
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from datetime import datetime, timedelta, timezone
from .utils import classify_account, enhanced_account_data, is_investment_account, is_retirement_account, is_credit_account, is_loan_account
import json
import os
from django.contrib.auth import get_user_model
from supabase import create_client, Client
import time
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.exceptions import ApiException as PlaidError
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest

logger = logging.getLogger(__name__)

class PlaidService:
    """
    Service class to handle Plaid API interactions, using Supabase as the data store.
    """
    
    def __init__(self):
        """Initialize the PlaidService"""
        self.adapter = SupabaseAdapter()
        
        # Plaid API credentials
        self.client_id = settings.PLAID_CLIENT_ID
        self.secret = settings.PLAID_SECRET
        self.plaid_environment = settings.PLAID_ENVIRONMENT
        
        logger.info(f"Initializing Plaid Service in {self.plaid_environment} mode")
    
    def create_link_token(self, user_id, update_mode=None, item_id=None, client_id=None) -> Optional[str]:
        """
        Create a Plaid Link token.
        
        Args:
            user_id: The user's ID or user object
            update_mode: Optional 'reconnect' for reconnecting existing items
            item_id: The Plaid item ID when reconnecting
            client_id: Custom client ID (defaults to PLAID_CLIENT_ID from settings)
            
        Returns:
            The link token if successful, None otherwise
        """
        try:
            # Handle user_id being a user object
            if hasattr(user_id, 'id'):
                user_id = str(user_id.id)
            else:
                user_id = str(user_id)
                
            plaid_client_id = client_id or settings.PLAID_CLIENT_ID
            plaid_secret = settings.PLAID_SECRET
            plaid_env = settings.PLAID_ENVIRONMENT
            
            configuration = plaid.Configuration(
                host=plaid.Environment.Sandbox,  # Using sandbox for development
                api_key={
                    'clientId': plaid_client_id,
                    'secret': plaid_secret,
                }
            )
            api_client = plaid.ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)
            
            # Create a Link token request
            request_args = {
                'client_name': "ConsulWealth Finance App",
                'country_codes': [CountryCode('US')],
                'language': 'en',
                'user': LinkTokenCreateRequestUser(
                    client_user_id=user_id
                ),
                'products': [
                    Products('transactions'),
                    Products('auth'),
                    Products('investments')
                ]
            }
            
            # Add redirect URI if defined
            if hasattr(settings, 'PLAID_REDIRECT_URI') and settings.PLAID_REDIRECT_URI:
                request_args['redirect_uri'] = settings.PLAID_REDIRECT_URI
                
            # Handle reconnection flow
            if update_mode == 'reconnect' and item_id:
                logger.info(f"Creating Link token for reconnection, item_id: {item_id}")
                # Get the access token for this item
                plaid_item = self.adapter.get_plaid_item_by_id(item_id)
                if plaid_item and plaid_item.get('access_token'):
                    # Use the access token for reconnection
                    request_args['access_token'] = plaid_item.get('access_token')
                    
                    # Ensure we're explicitly requesting investment permissions
                    # Instead of removing products, make sure 'investments' is included
                    if 'products' in request_args:
                        # Ensure investments is in the products list
                        has_investments = False
                        for product in request_args['products']:
                            if getattr(product, 'value', '') == 'investments':
                                has_investments = True
                                break
                        
                        if not has_investments:
                            request_args['products'].append(Products('investments'))
                    
                    logger.info("Configured Link token for update mode with investments product")
                else:
                    logger.error(f"Failed to find valid Plaid item with ID: {item_id}")
                    return None
            
            # Create the Link token request
            request = LinkTokenCreateRequest(**request_args)            
            response = client.link_token_create(request)
            return response['link_token']
            
        except Exception as e:
            logger.error(f"Error creating Plaid link token: {str(e)}")
            return None
    
    def exchange_public_token(self, user, public_token, is_reconnect=False, existing_item_id=None):
        """
        Exchange a public token for an access token and store it in Supabase
        
        Parameters:
        - user: The user object
        - public_token: The public token from Plaid Link
        - is_reconnect: Whether this is a reconnection (hard refresh)
        - existing_item_id: If reconnecting, the ID of the existing item
        """
        try:
            logger.info(f"Exchanging public token for user {user.id}, is_reconnect={is_reconnect}")
            
            # Create a real Plaid configuration
            configuration = Configuration(
                host=f"https://{self.plaid_environment}.plaid.com",
                api_key={
                    'clientId': self.client_id,
                    'secret': self.secret,
                }
            )
            
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)
            
            # Exchange the public token
            exchange_request = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            
            try:
                logger.info("Calling Plaid API to exchange public token")
                exchange_response = client.item_public_token_exchange(exchange_request)
                access_token = exchange_response['access_token']
                item_id = exchange_response['item_id']
                logger.info(f"Got access token and item_id: {item_id}")
                
                if is_reconnect and existing_item_id:
                    # For a hard refresh, update the existing item with the new access token
                    # and record this as a hard refresh
                    plaid_item = self.adapter.get_plaid_item_by_id(existing_item_id)
                    if plaid_item:
                        logger.info(f"Found existing item for update: {existing_item_id}")
                        
                        # Try to update status first (since this uses the enhanced fields)
                        try:
                            now = datetime.now(timezone.utc).isoformat()
                            next_refresh = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
                            
                            self.adapter.update_plaid_item_status(
                                existing_item_id, 
                                status='active',
                                update_type='hard',
                                last_update=now,
                                next_hard_refresh=next_refresh
                            )
                            
                            # Now try to update the access token separately
                            try:
                                # Use direct SQL update for critical field
                                update_response = self.adapter.client.table('plaid_items').update({
                                    'access_token': access_token,
                                    'item_id': item_id
                                }).eq('id', plaid_item['id']).execute()
                                
                                if not update_response.data:
                                    logger.error(f"Failed to update access token for item {existing_item_id}")
                            except Exception as token_error:
                                logger.error(f"Error updating access token: {str(token_error)}")
                        except Exception as status_error:
                            logger.error(f"Error updating item status: {str(status_error)}")
                            
                        # Try to update institution information while we're reconnecting
                        try:
                            # Get item information which includes the institution_id
                            item_response = client.item_get(ItemGetRequest(access_token=access_token))
                            item_data = self._plaid_object_to_dict(item_response)
                            institution_id = item_data.get('item', {}).get('institution_id')
                            
                            if institution_id:
                                # Get institution info (name, logo, etc)
                                try:
                                    inst_response = client.institutions_get_by_id(InstitutionsGetByIdRequest(
                                        institution_id=institution_id,
                                        country_codes=[CountryCode('US')]
                                    ))
                                    inst_data = self._plaid_object_to_dict(inst_response)
                                    
                                    # Get institution details
                                    institution_name = inst_data.get('institution', {}).get('name', 'Unknown Bank')
                                    institution_logo = inst_data.get('institution', {}).get('logo')
                                    
                                    logger.info(f"Updated institution info during reconnect: {institution_name} (ID: {institution_id})")
                                    
                                    # Update the Plaid item with institution info
                                    self.adapter.client.table('plaid_items').update({
                                        'institution_id': institution_id,
                                        'institution_name': institution_name,
                                        'institution_logo': institution_logo
                                    }).eq('id', plaid_item['id']).execute()
                                except Exception as inst_error:
                                    logger.warning(f"Could not get institution details during reconnect: {str(inst_error)}")
                        except Exception as e:
                            logger.error(f"Error updating institution info during reconnect: {str(e)}")
                        
                        logger.info(f"Updated existing Plaid item during hard refresh: {existing_item_id}")
                        
                        # After storing the item, sync accounts
                        accounts, investment_accounts = self.sync_accounts(user, is_reconnect=True, existing_item_id=existing_item_id)
                        
                        # Now sync investment holdings if there are investment accounts
                        if investment_accounts:
                            logger.info(f"Found {len(investment_accounts)} investment accounts to sync after reconnect")
                            self.sync_all_investment_holdings(
                                user_id=str(user.id),
                                plaid_item_id=existing_item_id,
                                investment_accounts=investment_accounts
                            )
                        
                        # Sync transactions for the last 90 days
                        end_date = datetime.now().date()
                        start_date = end_date - timedelta(days=90)
                        start_date_str = start_date.isoformat()
                        end_date_str = end_date.isoformat()

                        logger.info(f"Syncing initial transactions from {start_date_str} to {end_date_str}")
                        transactions = self.sync_transactions(user, start_date_str, end_date_str)
                        logger.info(f"Synced {len(transactions)} initial transactions after reconnect")
                        
                        return True
                    else:
                        logger.error(f"No existing Plaid item found with ID: {existing_item_id}")
                        # Fall back to creating a new item instead of failing
                        logger.info("Falling back to new item creation")
                        is_reconnect = False  # Switch to new item flow
                
                if not is_reconnect:
                    # For a new connection, store as a new Plaid item
                    # In a real integration, you would get this from Plaid metadata
                    institution_id = "ins_sandbox"  # This would come from Plaid metadata
                    
                    logger.info(f"Storing new Plaid item for user {user.id}, institution_id={institution_id}")
                    
                    # Try to get institution info from Plaid
                    try:
                        # Get item information which includes the institution_id
                        item_response = client.item_get(ItemGetRequest(access_token=access_token))
                        item_data = self._plaid_object_to_dict(item_response)
                        institution_id = item_data.get('item', {}).get('institution_id', institution_id)
                        
                        # Get institution info (name, logo, etc)
                        if institution_id:
                            inst_response = client.institutions_get_by_id(InstitutionsGetByIdRequest(
                                institution_id=institution_id,
                                country_codes=[CountryCode('US')]
                            ))
                            inst_data = self._plaid_object_to_dict(inst_response)
                            
                            # Get institution details
                            institution_name = inst_data.get('institution', {}).get('name', 'Unknown Bank')
                            institution_logo = inst_data.get('institution', {}).get('logo')
                            
                            logger.info(f"Found institution: {institution_name} (ID: {institution_id})")
                            
                            # Store the Plaid item with institution info
                            plaid_item_id = self.adapter.store_plaid_item(
                                user_id=str(user.id),
                                item_id=item_id,
                                access_token=access_token,
                                institution_id=institution_id,
                                institution_name=institution_name,
                                institution_logo=institution_logo
                            )
                        else:
                            logger.warning("No institution_id found, using default value")
                            plaid_item_id = self.adapter.store_plaid_item(
                                user_id=str(user.id),
                                item_id=item_id,
                                access_token=access_token,
                                institution_id=institution_id
                            )
                    except Exception as inst_error:
                        logger.error(f"Error getting institution info: {str(inst_error)}")
                        # Fall back to just storing the item without institution info
                        plaid_item_id = self.adapter.store_plaid_item(
                            user_id=str(user.id),
                            item_id=item_id,
                            access_token=access_token,
                            institution_id=institution_id
                        )
                    
                    if plaid_item_id:
                        logger.info(f"Successfully stored new Plaid item: {plaid_item_id}")
                        # After storing the item, sync accounts
                        accounts, investment_accounts = self.sync_accounts(user)
                        
                        # Now sync investment holdings if there are investment accounts
                        if investment_accounts:
                            logger.info(f"Found {len(investment_accounts)} investment accounts to sync for new connection")
                            self.sync_all_investment_holdings(
                                user_id=str(user.id),
                                plaid_item_id=plaid_item_id,
                                investment_accounts=investment_accounts
                            )

                        # Sync transactions for the last 90 days
                        end_date = datetime.now().date()
                        start_date = end_date - timedelta(days=90)
                        start_date_str = start_date.isoformat()
                        end_date_str = end_date.isoformat()

                        logger.info(f"Syncing initial transactions from {start_date_str} to {end_date_str} for new connection")
                        transactions = self.sync_transactions(user, start_date_str, end_date_str)
                        logger.info(f"Synced {len(transactions)} initial transactions for new connection")
                        
                        return True
                    else:
                        logger.error("Failed to store Plaid item, adapter returned None")
                    
                    return False
            except plaid.ApiException as e:
                response_body = json.loads(e.body)
                error_details = response_body.get('error_message', str(e))
                logger.error(f"Plaid API error: {error_details}", exc_info=True)
                raise Exception(f"Plaid API error: {error_details}")
                
        except Exception as e:
            logger.error(f"Error exchanging public token: {str(e)}", exc_info=True)
            raise
    
    def _plaid_object_to_dict(self, plaid_object):
        """
        Convert a Plaid API response object to a dictionary
        
        Args:
            plaid_object: A Plaid API response object
            
        Returns:
            A dictionary representation of the Plaid object
        """
        try:
            # If it's already a dict, return it
            if isinstance(plaid_object, dict):
                return plaid_object
            
            # If it has a to_dict method (Plaid API objects do), use it
            if hasattr(plaid_object, 'to_dict'):
                return plaid_object.to_dict()
            
            # If it's a list, convert each item
            if isinstance(plaid_object, list):
                return [self._plaid_object_to_dict(item) for item in plaid_object]
            
            # For other objects, try to convert to dict if possible
            if hasattr(plaid_object, '__dict__'):
                return {k: self._plaid_object_to_dict(v) for k, v in plaid_object.__dict__.items() 
                       if not k.startswith('_')}
            
            # Otherwise return as is
            return plaid_object
        except Exception as e:
            logger.error(f"Error converting Plaid object to dict: {str(e)}")
            # If conversion fails, return an empty dict to avoid breaking processing
            return {}

    def sync_accounts(self, user, is_reconnect=False, existing_item_id=None):
        """Sync accounts for a user from Plaid to our database"""
        try:
            logger.info(f"Syncing accounts for user {user.id}, is_reconnect={is_reconnect}")
            
            # Get all Plaid items for the user
            plaid_items = self.adapter.get_plaid_items(str(user.id))
            
            if not plaid_items:
                logger.warning(f"No Plaid items found for user {user.id}")
                return []
            
            # Track all synced accounts
            all_accounts = []
            investment_accounts = []
            
            # If we're reconnecting, get the existing item's account_ids to match later
            existing_account_ids = {}
            if is_reconnect and existing_item_id:
                logger.info(f"This is a reconnection for item {existing_item_id} - will attempt to update existing accounts")
                try:
                    # Get all the user's accounts
                    all_user_accounts = self.adapter.get_accounts(str(user.id))
                    
                    # Filter those with the matching plaid_item_id
                    for account in all_user_accounts:
                        if account.get('plaid_item_id') == existing_item_id:
                            account_name = account.get('name', '').lower()
                            # Store by both ID and normalized name for matching
                            if 'id' in account:
                                existing_account_ids[account['id']] = account
                            if account_name:
                                existing_account_ids[account_name] = account
                    
                    logger.info(f"Found {len(existing_account_ids)} existing accounts to match for reconnection")
                except Exception as account_error:
                    logger.error(f"Error getting existing accounts for reconnection: {str(account_error)}")
            
            # For each Plaid item, get and store accounts
            for item in plaid_items:
                logger.info(f"Processing Plaid item {item.get('id')}")
                
                # Get access token
                access_token = item.get('access_token')
                if not access_token:
                    logger.error(f"No access token found for item {item.get('id')}")
                    continue
                
                # Always get real accounts from Plaid API
                # Create a Plaid API client
                configuration = Configuration(
                    host=f"https://{self.plaid_environment}.plaid.com",
                    api_key={
                        'clientId': self.client_id,
                        'secret': self.secret,
                    }
                )
                
                api_client = ApiClient(configuration)
                client = plaid_api.PlaidApi(api_client)
                
                try:
                    # Get accounts from Plaid
                    logger.info(f"Fetching real accounts from Plaid with access token {access_token[:5]}...")
                    accounts_request = AccountsGetRequest(access_token=access_token)
                    accounts_response = client.accounts_get(accounts_request)
                    
                    # Convert the API response to a dictionary
                    accounts_data = self._plaid_object_to_dict(accounts_response)
                    accounts = accounts_data.get('accounts', [])
                    
                    logger.info(f"Found {len(accounts)} real accounts")
                except plaid.ApiException as e:
                    response_body = json.loads(e.body)
                    logger.error(f"Plaid API error: {response_body.get('error_code')} - {response_body.get('error_message')}")
                    
                    if response_body.get('error_code') == 'ITEM_LOGIN_REQUIRED':
                        # Update item status to indicate reconnection needed
                        self.adapter.update_plaid_item_status(
                            item.get('item_id'), 
                            status='login_required',
                            update_type='error'
                        )
                        
                    continue
                
                # Import utility functions
                from .utils import is_investment_account, enhanced_account_data
                
                # Process each account
                for account in accounts:
                    try:
                        # Get enhanced data
                        enhanced_data = enhanced_account_data(account)
                        
                        # Check if this is an investment account
                        account_is_investment = is_investment_account(account)
                        
                        # Basic account data that should always exist in schema
                        account_data = {
                            # Required fields for all accounts
                            'user_id': str(user.id),
                            'account_id': account.get('account_id'),
                            'name': account.get('name', 'Unnamed Account'),
                            'type': account.get('type', 'other'),
                            'subtype': account.get('subtype', '')
                        }
                        
                        # Always include balances since these are essential
                        if account.get('balances', {}).get('current') is not None:
                            account_data['current_balance'] = account.get('balances', {}).get('current', 0)
                        else:
                            account_data['current_balance'] = 0
                            
                        if account.get('balances', {}).get('available') is not None:
                            account_data['available_balance'] = account.get('balances', {}).get('available', 0)
                        else:
                            account_data['available_balance'] = 0
                        
                        # Include institution data
                        if item.get('institution_id'):
                            account_data['institution_id'] = item.get('institution_id')
                        
                        if item.get('institution_name'):
                            account_data['institution_name'] = item.get('institution_name')
                        
                        # Optional fields - only add if the column is known to exist
                        # Use a safe dictionary approach to avoid KeyErrors
                        
                        # Set account type flags safely using a dictionary instead of trying to directly set fields
                        # This ensures we only include fields that exist in the schema
                        account_flags = {
                            'is_investment': account_is_investment,
                            'is_investment_account': account_is_investment,
                            'is_plaid_synced': True,
                            'status': 'active'
                        }
                        
                        # Optional UI fields from enhanced data 
                        ui_fields = {}
                        if enhanced_data.get('color'):
                            ui_fields['color'] = enhanced_data.get('color')
                        if enhanced_data.get('icon_url'):
                            ui_fields['icon_url'] = enhanced_data.get('icon_url')
                            
                        # Plaid item ID - store as string to avoid UUID issues
                        if item.get('id'):
                            account_data['plaid_item_id'] = str(item.get('id'))
                        
                        # If we're reconnecting, try to find and update an existing account
                        if is_reconnect and existing_item_id and existing_account_ids:
                            # Try to find a match by name (case-insensitive) or account ID
                            account_name = account_data.get('name', '').lower()
                            account_id = account_data.get('account_id')
                            
                            # Look for matches
                            found_match = False
                            
                            # Try exact match by Plaid account_id first
                            for existing_key, existing_account in existing_account_ids.items():
                                if existing_account.get('account_id') == account_id:
                                    # Found an exact match - use this account's ID
                                    account_data['id'] = existing_account['id']
                                    logger.info(f"Found exact account_id match for reconnected account: {account_name}")
                                    found_match = True
                                    break
                            
                            # If no exact match found, try matching by name
                            if not found_match and account_name in existing_account_ids:
                                account_data['id'] = existing_account_ids[account_name]['id']
                                logger.info(f"Found name match for reconnected account: {account_name}")
                                found_match = True
                            
                            # For reconnected accounts with a match, we must force an update
                            if found_match:
                                logger.info(f"Updating existing account during reconnection: {account_data['name']}")
                        
                        # Merge all data dictionaries
                        # The adapter's _clean_account_data method will handle
                        # filtering out fields that don't exist in the database
                        account_data.update(account_flags)
                        account_data.update(ui_fields)
                        
                        # Store the account using the adapter
                        # The adapter will clean the data and handle schema differences
                        stored_account = self.adapter.store_account(str(user.id), account_data)
                        
                        if stored_account:
                            all_accounts.append(stored_account)
                            
                            # Add to investment accounts list if applicable
                            if account_is_investment:
                                logger.info(f"Added investment account {account.get('name')} for sync")
                                investment_accounts.append({
                                    'account_id': stored_account.get('id'),
                                    'plaid_account_id': account.get('account_id')
                                })
                    except Exception as account_error:
                        logger.error(f"Error processing account {account.get('account_id')}: {str(account_error)}")
                        continue
            
            return all_accounts, investment_accounts
        except Exception as e:
            logger.error(f"Error syncing accounts: {str(e)}")
            return [], []
    
    def sync_investment_holdings(self, user_id, plaid_item_id, account_id=None, plaid_account_id=None, demo_mode=None):
        """Sync investment holdings for a specific account or all investment accounts for a user"""
        try:
            logger.info(f"Syncing investment holdings for user {user_id}, plaid_item {plaid_item_id}")
            
            # Create a Plaid API client
            configuration = Configuration(
                host=f"https://{self.plaid_environment}.plaid.com",
                api_key={
                    'clientId': self.client_id,
                    'secret': self.secret,
                }
            )
            
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)
            
            # Get the Plaid item for the access token
            item = self.adapter.get_plaid_item_by_id(plaid_item_id)
            if not item:
                logger.error(f"Could not find Plaid item with ID {plaid_item_id}")
                return False
            
            access_token = item.get('access_token')
            if not access_token:
                logger.error(f"No access token found for Plaid item {plaid_item_id}")
                return False
            
            # Get investment holdings from Plaid
            try:
                holdings_request = InvestmentsHoldingsGetRequest(access_token=access_token)
                holdings_response = client.investments_holdings_get(holdings_request)
                
                # Convert to Python dict for easier access
                holdings_data = self._plaid_object_to_dict(holdings_response)
                
                holdings = holdings_data.get('holdings', [])
                securities = holdings_data.get('securities', [])
                accounts = holdings_data.get('accounts', [])
                
                logger.info(f"Retrieved {len(holdings)} holdings, {len(securities)} securities, and {len(accounts)} accounts from Plaid")
            except plaid.ApiException as e:
                # Handle Plaid API errors
                error_dict = {}
                try:
                    error_dict = json.loads(e.body)
                    logger.error(f"Plaid API error: {error_dict.get('error_code')} - {error_dict.get('error_message')}")
                except Exception:
                    logger.error(f"Plaid API error: {str(e)}")
                
                # Update item status if needed
                if error_dict.get('error_code') == 'ITEM_LOGIN_REQUIRED':
                    self.adapter.update_plaid_item_status(
                        item.get('item_id'),
                        status='login_required',
                        update_type='error'
                    )
                return False
            except Exception as e:
                logger.error(f"Error getting investment holdings from Plaid: {str(e)}")
                return False
            
            # Process securities first - we need to store them before holdings
            for security in securities:
                try:
                    # Check if security already exists
                    security_id = security.get('security_id')
                    if not security_id:
                        logger.warning(f"Security missing security_id: {security}")
                        continue
                    
                    # Store the security in the database
                    db_security_id = self.adapter.store_security(security)
                    if not db_security_id:
                        logger.warning(f"Failed to store security: {security_id}")
                except Exception as sec_error:
                    logger.error(f"Error processing security: {str(sec_error)}")
            
            # Filter accounts if needed
            if account_id:
                # Filter for a specific account
                logger.info(f"Filtering for account_id: {account_id}")
                
                # Instead of using get_account_by_plaid_id, query directly
                try:
                    # Try querying directly from the accounts table - use ID not account_id
                    response = self.adapter.client.table('accounts').select('*').eq('id', account_id).execute()
                    
                    if response.data and len(response.data) > 0:
                        account = response.data[0]
                        plaid_account_id = account.get('account_id')
                        
                        if not plaid_account_id:
                            logger.error(f"Account {account_id} does not have a Plaid account_id")
                            return False
                    else:
                        logger.error(f"Could not find account with ID {account_id}")
                        return False
                except Exception as account_error:
                    logger.error(f"Error finding account {account_id}: {str(account_error)}")
                    return False
            
            # Process holdings
            total_processed = 0
            total_portfolio_value = 0
            processed_account_ids = set()
            
            for holding in holdings:
                try:
                    holding_account_id = holding.get('account_id')
                    if not holding_account_id:
                        logger.warning(f"Holding missing account_id: {holding}")
                        continue
                    
                    # Skip if we're filtering by account_id and this doesn't match
                    if plaid_account_id and holding_account_id != plaid_account_id:
                        continue
                    
                    # Get our database account that corresponds to this Plaid account_id
                    # Instead of using get_account_by_plaid_id, query directly
                    try:
                        account_response = self.adapter.client.table('accounts').select('*').eq('account_id', holding_account_id).execute()
                        
                        if account_response.data and len(account_response.data) > 0:
                            db_account = account_response.data[0]
                        else:
                            logger.warning(f"No database account found for Plaid account_id: {holding_account_id}")
                            continue
                    except Exception as account_error:
                        logger.warning(f"Error querying account with Plaid ID {holding_account_id}: {str(account_error)}")
                        continue
                    
                    # Add to processed accounts set
                    processed_account_ids.add(db_account['id'])
                    
                    # Get the security associated with this holding
                    security_id = holding.get('security_id')
                    if not security_id:
                        logger.warning(f"Holding missing security_id: {holding}")
                        continue
                    
                    # Find the corresponding security in our securities list
                    matching_security = next((s for s in securities if s.get('security_id') == security_id), None)
                    if not matching_security:
                        logger.warning(f"No matching security found for security_id: {security_id}")
                        continue
                    
                    # Get the database ID for this security - query directly
                    try:
                        security_response = self.adapter.client.table('securities').select('*').eq('security_id', security_id).execute()
                        
                        if security_response.data and len(security_response.data) > 0:
                            db_security = security_response.data[0]
                            db_security_id = db_security['id']
                        else:
                            logger.warning(f"Security not found in database: {security_id}")
                            continue
                    except Exception as sec_query_error:
                        logger.warning(f"Error querying security with ID {security_id}: {str(sec_query_error)}")
                        continue
                    
                    # Add the security name to the holding for better logging
                    holding['security_name'] = matching_security.get('name', 'Unknown')
                    
                    # Store the holding
                    db_holding_id = self.adapter.store_holding(
                        db_account['id'], 
                        db_security_id, 
                        holding
                    )
                    
                    if db_holding_id:
                        # Add to the total portfolio value
                        institution_value = holding.get('institution_value', 0)
                        if institution_value:
                            try:
                                total_portfolio_value += float(institution_value)
                            except (ValueError, TypeError):
                                pass
                        
                        logger.info(f"Stored holding: {holding.get('security_name')} ({holding.get('quantity')} shares)")
                        total_processed += 1
                    else:
                        logger.warning(f"Failed to store holding: {holding.get('security_name')}")
                    
                except Exception as holding_error:
                    logger.error(f"Error processing holding: {str(holding_error)}")
            
            # Update the account's portfolio value for each processed account
            for account_id in processed_account_ids:
                try:
                    # Update the account's portfolio value directly
                    self.adapter.client.table('accounts').update({
                        'portfolio_value': total_portfolio_value,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }).eq('id', account_id).execute()
                    
                    logger.info(f"Updated portfolio value for account {account_id}: ${total_portfolio_value:.2f}")
                except Exception as portfolio_error:
                    logger.error(f"Error updating portfolio value: {str(portfolio_error)}")
            
            logger.info(f"Processed {total_processed} holdings with total value ${total_portfolio_value:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error in sync_investment_holdings: {str(e)}")
            return False
    
    def sync_transactions(self, user, start_date, end_date):
        """Sync transactions for a user from Plaid to Supabase"""
        try:
            logger.info(f"Syncing transactions for user {user.id} from {start_date} to {end_date}")
            
            # Get all Plaid items for the user
            plaid_items = self.adapter.get_plaid_items(str(user.id))
            
            if not plaid_items:
                logger.warning(f"No Plaid items found for user {user.id}, cannot sync transactions")
                return []
            
            # Create Plaid API client configuration
            configuration = Configuration(
                host=f"https://{self.plaid_environment}.plaid.com",
                api_key={
                    'clientId': self.client_id,
                    'secret': self.secret,
                }
            )
            
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)
            
            # Track all transactions synced
            all_transactions = []
            
            # Format dates properly if they're strings
            if isinstance(start_date, str):
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                start_date_obj = start_date
            
            if isinstance(end_date, str):
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                end_date_obj = end_date
            
            # For each Plaid item, get transactions
            for item in plaid_items:
                try:
                    access_token = item.get('access_token')
                    if not access_token:
                        logger.error(f"No access token found for item {item.get('id')}")
                        continue
                    
                    logger.info(f"Fetching transactions for Plaid item {item.get('id')}")
                    
                    # Build the transactions get request
                    options = TransactionsGetRequestOptions(
                        count=500  # Max number of transactions per request
                    )
                    
                    request = TransactionsGetRequest(
                        access_token=access_token,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                        options=options
                    )
                    
                    try:
                        # Get initial response
                        response = client.transactions_get(request)
                        transactions_data = self._plaid_object_to_dict(response)
                        
                        # Get total transactions and process what we received
                        total_transactions = transactions_data.get('total_transactions', 0)
                        transactions = transactions_data.get('transactions', [])
                        
                        logger.info(f"Retrieved {len(transactions)} of {total_transactions} transactions from Plaid")
                        
                        # Add account info to each transaction
                        accounts_map = {}
                        for account in transactions_data.get('accounts', []):
                            accounts_map[account.get('account_id')] = account
                        
                        # Get a mapping of Plaid account IDs to Supabase account UUIDs
                        try:
                            # Fetch all accounts for this user
                            supabase_accounts = self.adapter.get_accounts(str(user.id))
                            account_id_to_uuid = {}
                            
                            for acct in supabase_accounts:
                                if 'account_id' in acct and 'id' in acct:
                                    account_id_to_uuid[acct['account_id']] = acct['id']
                                elif 'plaid_account_id' in acct and 'id' in acct:
                                    account_id_to_uuid[acct['plaid_account_id']] = acct['id']
                            
                            logger.info(f"Found {len(account_id_to_uuid)} account ID to UUID mappings")
                        except Exception as account_error:
                            logger.error(f"Error fetching account mappings: {str(account_error)}")
                            account_id_to_uuid = {}
                        
                        # Process and format transactions for our database
                        formatted_transactions = []
                        for tx in transactions:
                            try:
                                # Basic required fields
                                tx_data = {
                                    'id': str(uuid.uuid4()),
                                    'transaction_id': tx.get('transaction_id'),
                                    'amount': tx.get('amount', 0.0),  # Plaid uses positive for debit, negative for credit
                                    'date': tx.get('date'),
                                    'name': tx.get('name'),
                                    'pending': tx.get('pending', False),
                                    'user_id': str(user.id)  # Add user_id to every transaction
                                }
                                
                                # Add account_id - use UUID mapping if available, otherwise skip this transaction
                                plaid_account_id = tx.get('account_id')
                                if plaid_account_id in account_id_to_uuid:
                                    tx_data['account_id'] = account_id_to_uuid[plaid_account_id]
                                else:
                                    logger.warning(f"No UUID mapping found for Plaid account ID: {plaid_account_id}, skipping transaction")
                                    continue
                                
                                # Map merchant name and category
                                if tx.get('merchant_name'):
                                    tx_data['merchant_name'] = tx.get('merchant_name')
                                    
                                if tx.get('category'):
                                    tx_data['category'] = tx.get('category')[0] if isinstance(tx.get('category'), list) and tx.get('category') else tx.get('category')
                                
                                # Add payment metadata if available
                                payment_meta = tx.get('payment_meta', {})
                                if payment_meta:
                                    if payment_meta.get('reference_number'):
                                        tx_data['reference_number'] = payment_meta.get('reference_number')
                                        
                                    if payment_meta.get('payee'):
                                        tx_data['payee'] = payment_meta.get('payee')
                                        
                                    if payment_meta.get('payer'):
                                        tx_data['payer'] = payment_meta.get('payer')
                                    
                                    if payment_meta.get('payment_method'):
                                        tx_data['payment_method'] = payment_meta.get('payment_method')
                                
                                # Add location data if available
                                if tx.get('location'):
                                    tx_data['location'] = json.dumps(tx.get('location'))
                                    
                                # Add payment channel if available
                                if tx.get('payment_channel'):
                                    tx_data['payment_channel'] = tx.get('payment_channel')
                                    
                                # Add personal finance category if available
                                if tx.get('personal_finance_category'):
                                    pfc = tx.get('personal_finance_category', {})
                                    if pfc.get('primary'):
                                        tx_data['category_id'] = pfc.get('primary')
                                        
                                    if pfc.get('detailed'):
                                        tx_data['subcategory'] = pfc.get('detailed')
                                        
                                # Add currency codes if available
                                if tx.get('iso_currency_code'):
                                    tx_data['iso_currency_code'] = tx.get('iso_currency_code')
                                    
                                if tx.get('unofficial_currency_code'):
                                    tx_data['unofficial_currency_code'] = tx.get('unofficial_currency_code')
                                    
                                # Add other useful fields from Plaid
                                if tx.get('website'):
                                    tx_data['website'] = tx.get('website')
                                    
                                if tx.get('authorized_date'):
                                    tx_data['authorized_date'] = tx.get('authorized_date')
                                    
                                # Serialize the transaction data using our utility
                                from .utils import serialize_for_supabase
                                tx_data = serialize_for_supabase(tx_data)
                                    
                                # Add to formatted transactions
                                formatted_transactions.append(tx_data)
                            except Exception as tx_error:
                                logger.error(f"Error formatting transaction: {str(tx_error)}")
                                continue
                        
                        # Add formatted transactions to our collection
                        all_transactions.extend(formatted_transactions)
                        
                        # Handle pagination if needed
                        has_more = transactions_data.get('has_more', False)
                        offset = len(transactions)
                        
                        while has_more and offset < total_transactions:
                            # Update options with offset
                            options = TransactionsGetRequestOptions(
                                count=500,
                                offset=offset
                            )
                            
                            request = TransactionsGetRequest(
                                access_token=access_token,
                                start_date=start_date_obj,
                                end_date=end_date_obj,
                                options=options
                            )
                            
                            logger.info(f"Fetching more transactions, offset {offset}")
                            
                            # Get next batch
                            response = client.transactions_get(request)
                            transactions_data = self._plaid_object_to_dict(response)
                            
                            transactions = transactions_data.get('transactions', [])
                            has_more = transactions_data.get('has_more', False)
                            
                            logger.info(f"Retrieved {len(transactions)} more transactions from Plaid")
                            
                            # Process this batch of transactions
                            formatted_transactions = []
                            for tx in transactions:
                                try:
                                    # Same formatting as above
                                    tx_data = {
                                        'id': str(uuid.uuid4()),
                                        'transaction_id': tx.get('transaction_id'),
                                        'amount': tx.get('amount', 0.0),
                                        'date': tx.get('date'),
                                        'name': tx.get('name'),
                                        'pending': tx.get('pending', False),
                                        'user_id': str(user.id)  # Add user_id to every transaction
                                    }
                                    
                                    # Add account_id - use UUID mapping if available, otherwise skip this transaction
                                    plaid_account_id = tx.get('account_id')
                                    if plaid_account_id in account_id_to_uuid:
                                        tx_data['account_id'] = account_id_to_uuid[plaid_account_id]
                                    else:
                                        logger.warning(f"No UUID mapping found for Plaid account ID: {plaid_account_id}, skipping transaction")
                                        continue
                                    
                                    if tx.get('merchant_name'):
                                        tx_data['merchant_name'] = tx.get('merchant_name')
                                        
                                    if tx.get('category'):
                                        tx_data['category'] = tx.get('category')[0] if isinstance(tx.get('category'), list) and tx.get('category') else tx.get('category')
                                    
                                    payment_meta = tx.get('payment_meta', {})
                                    if payment_meta:
                                        if payment_meta.get('reference_number'):
                                            tx_data['reference_number'] = payment_meta.get('reference_number')
                                        if payment_meta.get('payee'):
                                            tx_data['payee'] = payment_meta.get('payee')
                                    
                                    account = accounts_map.get(tx.get('account_id'))
                                    if account:
                                        tx_data['account_name'] = account.get('name')
                                        
                                    formatted_transactions.append(tx_data)
                                except Exception as tx_error:
                                    logger.error(f"Error processing transaction {tx.get('transaction_id')}: {str(tx_error)}")
                            
                            # Add formatted transactions to our collection
                            all_transactions.extend(formatted_transactions)
                            
                            # Update offset for next page
                            offset += len(transactions)
                        
                        # Record that we've done a successful sync
                        self.adapter.record_soft_refresh(item.get('item_id'))
                        
                    except plaid.ApiException as e:
                        # Handle Plaid API errors
                        try:
                            response_body = json.loads(e.body)
                            error_code = response_body.get('error_code')
                            error_message = response_body.get('error_message')
                            logger.error(f"Plaid API error: {error_code} - {error_message}")
                            
                            # Update item status for specific errors
                            if error_code == 'ITEM_LOGIN_REQUIRED':
                                self.adapter.update_plaid_item_status(
                                    item.get('item_id'),
                                    status='login_required',
                                    update_type='error'
                                )
                        except Exception:
                            logger.error(f"Plaid API error: {str(e)}")
                        
                        continue
                    except Exception as e:
                        logger.error(f"Error getting transactions from Plaid: {str(e)}")
                        continue
                
                except Exception as item_error:
                    logger.error(f"Error processing Plaid item {item.get('id')}: {str(item_error)}")
                    continue
            
            # Store all transactions in Supabase if we have any
            if all_transactions:
                logger.info(f"Storing {len(all_transactions)} transactions in Supabase")
                self.adapter.store_transactions(all_transactions)
            else:
                logger.warning("No transactions found to store")
            
            return all_transactions
        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            logger.exception("Full exception details:")
            return []
    
    def refresh_accounts(self, user):
        """Refresh accounts for a user from Plaid"""
        try:
            logger.info(f"Refreshing accounts for user {user.id}")
            
            # Call the sync_accounts method to get updated account data
            accounts, investment_accounts = self.sync_accounts(user)
            
            # If we have investment accounts, also refresh holdings for each account
            if investment_accounts:
                logger.info(f"Refreshing investment holdings for {len(investment_accounts)} accounts")
                
                # Get all Plaid items for the user
                plaid_items = self.adapter.get_plaid_items(str(user.id))
                
                if not plaid_items:
                    logger.warning(f"No Plaid items found for user {user.id}, can't sync investment holdings")
                else:
                    # Use the first item for now - in the future, we might want to match by institution
                    plaid_item_id = plaid_items[0].get('id')
                    
                    # Use the optimized method to sync all investment holdings at once
                    self.sync_all_investment_holdings(
                        user_id=str(user.id),
                        plaid_item_id=plaid_item_id,
                        investment_accounts=investment_accounts
                    )
                
            return accounts
            
        except Exception as e:
            logger.error(f"Error refreshing accounts: {str(e)}")
            return []
    
    def refresh_transactions(self, user, start_date, end_date):
        """Refresh transactions for a user (soft refresh)"""
        try:
            logger.info(f"Performing soft refresh of transactions for user {user.id} from {start_date} to {end_date}")
            
            # Ensure dates are in the proper format
            if isinstance(start_date, str):
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                except ValueError:
                    logger.error(f"Invalid start_date format: {start_date}. Expected YYYY-MM-DD.")
                    return []
            
            if isinstance(end_date, str):
                try:
                    datetime.strptime(end_date, '%Y-%m-%d')
                except ValueError:
                    logger.error(f"Invalid end_date format: {end_date}. Expected YYYY-MM-DD.")
                    return []
            
            # Call the sync_transactions method with the provided parameters
            return self.sync_transactions(user, start_date, end_date)
        except Exception as e:
            logger.error(f"Error refreshing transactions: {str(e)}")
            logger.exception("Full exception details:")
            return []
        
    def get_plaid_status(self, user):
        """Get Plaid connection status for a user"""
        try:
            # Get all Plaid items for the user
            items = self.adapter.get_plaid_items(str(user.id))
            
            if not items:
                return {
                    'connected': False,
                    'institutions': [],
                    'accounts_count': 0,
                    'last_update': None,
                    'next_hard_refresh': None
                }
            
            # Get accounts count
            accounts = self.adapter.get_accounts(str(user.id))
            
            # Build the status response
            institutions = []
            last_update = None
            next_hard_refresh = None
            
            for item in items:
                # For each item, get its status
                institution_name = item.get('institution_name', 'Unknown Bank')
                
                # Track the most recent update across all items
                item_last_update = item.get('last_successful_update')
                if not last_update or (item_last_update and item_last_update > last_update):
                    last_update = item_last_update
                
                # Track the earliest hard refresh needed
                item_next_hard_refresh = item.get('next_hard_refresh')
                if not next_hard_refresh or (item_next_hard_refresh and item_next_hard_refresh < next_hard_refresh):
                    next_hard_refresh = item_next_hard_refresh
                
                # Build institution data
                institution_data = {
                    'id': item.get('id'),
                    'name': institution_name,
                    'institution_name': institution_name,
                    'institution_id': item.get('institution_id'),
                    'connection_status': item.get('connection_status', 'unknown'),
                    'last_update': item.get('last_successful_update'),
                    'item_id': item.get('item_id')
                }
                
                if item.get('institution_logo'):
                    institution_data['logo'] = item.get('institution_logo')
                
                institutions.append(institution_data)
            
            return {
                'connected': True,
                'institutions': institutions,
                'accounts_count': len(accounts),
                'last_update': last_update,
                'next_hard_refresh': next_hard_refresh
            }
            
        except Exception as e:
            logger.error(f"Error getting Plaid status: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def is_institution_connected(self, user_id, institution_id):
        """Check if an institution is already connected for a user"""
        connected_institutions = self.adapter.get_connected_institutions(user_id)
        return institution_id in connected_institutions if institution_id else False
        
    def check_items_needing_refresh(self, user=None):
        """Check for items needing refresh and schedule them"""
        try:
            user_id = str(user.id) if user else None
            
            # Get items needing soft refresh
            soft_refresh_items = self.adapter.get_items_needing_refresh(user_id, 'soft')
            logger.info(f"Found {len(soft_refresh_items)} items needing soft refresh")
            
            # Get items needing hard refresh
            hard_refresh_items = self.adapter.get_items_needing_refresh(user_id, 'hard')
            logger.info(f"Found {len(hard_refresh_items)} items needing hard refresh")
            
            return {
                'soft_refresh_needed': soft_refresh_items,
                'hard_refresh_needed': hard_refresh_items
            }
        except Exception as e:
            logger.error(f"Error checking items needing refresh: {str(e)}")
            return {
                'soft_refresh_needed': [],
                'hard_refresh_needed': []
            }

    def sync_all_investment_holdings(self, user_id, plaid_item_id, investment_accounts):
        """
        Sync all investment holdings for multiple accounts in a single Plaid API call.
        
        Args:
            user_id (str): The user ID
            plaid_item_id (str): The Plaid item ID
            investment_accounts (list): List of investment accounts to sync
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Syncing all investment holdings for user {user_id}, plaid_item {plaid_item_id}")
            
            if not investment_accounts:
                logger.info("No investment accounts to sync")
                return True
                
            # Create a Plaid API client
            configuration = Configuration(
                host=f"https://{self.plaid_environment}.plaid.com",
                api_key={
                    'clientId': self.client_id,
                    'secret': self.secret,
                }
            )
            
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)
            
            # Get the Plaid item for the access token
            item = self.adapter.get_plaid_item_by_id(plaid_item_id)
            if not item:
                logger.error(f"Could not find Plaid item with ID {plaid_item_id}")
                return False
            
            access_token = item.get('access_token')
            if not access_token:
                logger.error(f"No access token found for Plaid item {plaid_item_id}")
                return False
            
            # Make a single API call to get all investment holdings
            try:
                holdings_request = InvestmentsHoldingsGetRequest(access_token=access_token)
                holdings_response = client.investments_holdings_get(holdings_request)
                
                # Convert to Python dict for easier access
                holdings_data = self._plaid_object_to_dict(holdings_response)
                
                holdings = holdings_data.get('holdings', [])
                securities = holdings_data.get('securities', [])
                accounts = holdings_data.get('accounts', [])
                
                logger.info(f"Retrieved {len(holdings)} holdings, {len(securities)} securities, and {len(accounts)} accounts from Plaid")
            except plaid.ApiException as e:
                # Handle Plaid API errors
                error_dict = {}
                try:
                    error_dict = json.loads(e.body)
                    logger.error(f"Plaid API error: {error_dict.get('error_code')} - {error_dict.get('error_message')}")
                except Exception:
                    logger.error(f"Plaid API error: {str(e)}")
                
                # Update item status if needed
                if error_dict.get('error_code') == 'ITEM_LOGIN_REQUIRED':
                    self.adapter.update_plaid_item_status(
                        item.get('item_id'),
                        status='login_required',
                        update_type='error'
                    )
                return False
            except Exception as e:
                logger.error(f"Error getting investment holdings from Plaid: {str(e)}")
                return False
            
            # Process securities once for all accounts
            for security in securities:
                try:
                    # Check if security already exists
                    security_id = security.get('security_id')
                    if not security_id:
                        logger.warning(f"Security missing security_id: {security}")
                        continue
                    
                    # Store the security in the database
                    db_security_id = self.adapter.store_security(security)
                    if not db_security_id:
                        logger.warning(f"Failed to store security: {security_id}")
                except Exception as sec_error:
                    logger.error(f"Error processing security: {str(sec_error)}")
            
            # Create mapping from Plaid account_ids to our database account IDs
            account_mapping = {}
            for inv_account in investment_accounts:
                db_account_id = inv_account.get('account_id')
                plaid_account_id = inv_account.get('plaid_account_id')
                if db_account_id and plaid_account_id:
                    account_mapping[plaid_account_id] = db_account_id
            
            # Process holdings for each account
            processed_accounts = set()
            account_portfolio_values = {}
            
            for holding in holdings:
                try:
                    holding_account_id = holding.get('account_id')
                    if not holding_account_id or holding_account_id not in account_mapping:
                        continue
                    
                    db_account_id = account_mapping[holding_account_id]
                    
                    # Get the security associated with this holding
                    security_id = holding.get('security_id')
                    if not security_id:
                        logger.warning(f"Holding missing security_id: {holding}")
                        continue
                    
                    # Find the corresponding security in our securities list
                    matching_security = next((s for s in securities if s.get('security_id') == security_id), None)
                    if not matching_security:
                        logger.warning(f"No matching security found for security_id: {security_id}")
                        continue
                    
                    # Get the database ID for this security
                    try:
                        security_response = self.adapter.client.table('securities').select('*').eq('security_id', security_id).execute()
                        
                        if security_response.data and len(security_response.data) > 0:
                            db_security = security_response.data[0]
                            db_security_id = db_security['id']
                        else:
                            logger.warning(f"Security not found in database: {security_id}")
                            continue
                    except Exception as sec_query_error:
                        logger.warning(f"Error querying security with ID {security_id}: {str(sec_query_error)}")
                        continue
                    
                    # Add the security name to the holding for better logging
                    holding['security_name'] = matching_security.get('name', 'Unknown')
                    
                    # Store the holding
                    db_holding_id = self.adapter.store_holding(
                        db_account_id, 
                        db_security_id, 
                        holding
                    )
                    
                    if db_holding_id:
                        # Add to the account's portfolio value
                        institution_value = holding.get('institution_value', 0)
                        if institution_value:
                            try:
                                value = float(institution_value)
                                processed_accounts.add(db_account_id)
                                if db_account_id not in account_portfolio_values:
                                    account_portfolio_values[db_account_id] = 0
                                account_portfolio_values[db_account_id] += value
                            except (ValueError, TypeError):
                                pass
                        
                        logger.info(f"Stored holding: {holding.get('security_name')} ({holding.get('quantity')} shares)")
                    else:
                        logger.warning(f"Failed to store holding: {holding.get('security_name')}")
                    
                except Exception as holding_error:
                    logger.error(f"Error processing holding: {str(holding_error)}")
            
            # Update each account's portfolio value
            for account_id, portfolio_value in account_portfolio_values.items():
                try:
                    # Update the account's portfolio value directly
                    self.adapter.client.table('accounts').update({
                        'portfolio_value': portfolio_value,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }).eq('id', account_id).execute()
                    
                    logger.info(f"Updated portfolio value for account {account_id}: ${portfolio_value:.2f}")
                except Exception as portfolio_error:
                    logger.error(f"Error updating portfolio value for account {account_id}: {str(portfolio_error)}")
            
            logger.info(f"Successfully synced holdings for {len(processed_accounts)} accounts")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing all investment holdings: {str(e)}")
            return False

class SupabaseService:
    """Singleton service for interacting with Supabase"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the Supabase client"""
        try:
            # Get configuration from Django settings
            self.supabase_url = settings.SUPABASE_URL
            self.supabase_key = settings.SUPABASE_KEY
            self.supabase_secret = settings.SUPABASE_SECRET
            
            # Validate settings
            if not self.supabase_url:
                raise ValueError("SUPABASE_URL is not set in settings or environment variables")
            if not self.supabase_key:
                raise ValueError("SUPABASE_KEY is not set in settings or environment variables")
                
            # Log configuration status (without revealing actual keys)
            logger.info(f"Initializing Supabase with URL: {self.supabase_url}")
            logger.info(f"Supabase Key: {'Present' if self.supabase_key else 'MISSING'}")
            logger.info(f"Supabase Secret: {'Present' if self.supabase_secret else 'Not set - admin operations may be limited'}")
            
            # Create the Supabase client
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {str(e)}")
            raise
    
    def sync_user_to_django(self, supabase_user):
        """
        Synchronize a Supabase user to a Django shadow user.
        Creates a new Django user if one doesn't exist, or updates an existing one.
        """
        User = get_user_model()
        supabase_id = supabase_user.id
        email = supabase_user.email
        
        try:
            # Try to find by supabase_id first
            user = User.objects.get(supabase_id=supabase_id)
            
            # Update fields if necessary
            updated_fields = []
            if user.email != email:
                user.email = email
                updated_fields.append('email')
            
            # Check for admin status in metadata
            if supabase_user.user_metadata:
                is_admin = supabase_user.user_metadata.get('is_admin', False)
                if user.is_staff != is_admin:
                    user.is_staff = is_admin
                    updated_fields.append('is_staff')
            
            if updated_fields:
                user.save(update_fields=updated_fields)
                logger.info(f"Updated shadow user {user.username} with Supabase data")
            
            return user
            
        except User.DoesNotExist:
            # Create a new shadow user
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure username is unique
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create a shadow user with unusable password
            user = User.objects.create(
                username=username,
                email=email,
                supabase_id=supabase_id
            )
            
            # Set unusable password since Supabase handles auth
            user.set_unusable_password()
            
            # Set admin status based on metadata
            if supabase_user.user_metadata:
                user.is_staff = supabase_user.user_metadata.get('is_admin', False)
                user.save(update_fields=['is_staff'])
            
            logger.info(f"Created shadow Django user '{username}' for Supabase user {supabase_id}")
            return user
    
    def sync_all_users(self):
        """
        Synchronize all Supabase users to Django shadow users.
        This can be run periodically to ensure Django and Supabase stay in sync.
        """
        try:
            # Get all users from Supabase
            response = self.client.auth.admin.list_users()
            supabase_users = response.users if response else []
            
            sync_count = 0
            for supabase_user in supabase_users:
                self.sync_user_to_django(supabase_user)
                sync_count += 1
            
            logger.info(f"Synchronized {sync_count} users from Supabase to Django")
            return sync_count
        except Exception as e:
            logger.error(f"Error synchronizing Supabase users: {str(e)}")
            raise
    
    def get_user_data(self, supabase_id):
        """Get user profile data from Supabase"""
        try:
            # Query profiles table for the user's data
            response = self.client.table('profiles').select('*').eq('id', supabase_id).execute()
            
            # If data exists with regular client, return it
            if response.data and len(response.data) > 0:
                return response.data[0]
                
            # If no data found, try with service role client which can bypass RLS policies
            logger.info(f"No profile found with regular client, trying service role for {supabase_id}")
            service_client = create_client(
                self.supabase_url,
                self.supabase_secret,  # Use service role key instead of anon key
            )
            
            # Try again with service client
            response = service_client.table('profiles').select('*').eq('id', supabase_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
                
            # If still nothing found, the profile truly doesn't exist
            return None
        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            return None
    
    def update_profile(self, user_id, profile_data):
        """Update or create a user profile."""
        try:
            # Add updated_at timestamp
            profile_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Handle empty/empty string values for all fields
            for key, value in list(profile_data.items()):
                # Convert empty strings to None for all fields
                if value == '':
                    profile_data[key] = None
            
            # Get current profile data first to check if it exists
            existing_profile = self.get_user_data(user_id)
            
            # Ensure email field is populated
            if 'email' not in profile_data or not profile_data.get('email'):
                # Try to get email from Django user model first
                try:
                    from django.contrib.auth.models import User
                    try:
                        django_user = User.objects.get(username=user_id)
                        profile_data['email'] = django_user.email
                        logger.info(f"Using Django user email: {profile_data['email']}")
                    except User.DoesNotExist:
                        logger.warning(f"No Django user found for {user_id}")
                except Exception as e:
                    logger.warning(f"Error getting Django user: {str(e)}")
                
                # If still no email, try to get from session
                if 'email' not in profile_data or not profile_data.get('email'):
                    try:
                        # Try to get from auth user if available
                        user = self.client.auth.get_user()
                        if user and hasattr(user, 'user') and user.user and user.user.email:
                            profile_data['email'] = user.user.email
                            logger.info(f"Using Supabase auth email: {profile_data['email']}")
                    except Exception as e:
                        logger.warning(f"Error getting Supabase user: {str(e)}")
                
                # Last resort - create a fallback email based on user_id
                if 'email' not in profile_data or not profile_data.get('email'):
                    # Hard-code the email for the known user
                    if user_id == '87fea98f-c633-4b41-ac83-731912da82f7':
                        profile_data['email'] = 'jwarner1437@gmail.com'
                    else:
                        profile_data['email'] = f"{user_id}@example.com"
                    logger.info(f"Using fallback email: {profile_data['email']}")
            
            # Use service role client to bypass RLS
            service_client = self.create_service_role_client()
            
            if existing_profile:
                logger.info(f"Updating existing profile for user {user_id}")
                # Use service role to update the profile
                result = service_client.table('profiles').update(
                    profile_data
                ).eq('id', user_id).execute()
                
                if result.data:
                    logger.info(f"Successfully updated profile for user {user_id}")
                    return result.data
                else:
                    logger.warning(f"Update returned no data for user {user_id}")
                    return existing_profile
            else:
                logger.info(f"Creating new profile for user {user_id}")
                # Create new profile with required fields
                profile_data['id'] = user_id
                profile_data['created_at'] = datetime.now(timezone.utc).isoformat()
                
                # Use service role to create profile
                result = service_client.table('profiles').insert(
                    profile_data
                ).execute()
                
                if result.data:
                    logger.info(f"Successfully created profile for user {user_id}")
                    return result.data
                else:
                    logger.warning(f"Insert returned no data for user {user_id}")
                    return None
                
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            raise e

    # Other methods for database operations
    def fetch_all_transactions(self, user_id=None):
        """Fetch all transactions from Supabase"""
        try:
            if user_id:
                response = self.client.table('transactions').select('*').eq('user_id', user_id).execute()
            else:
                response = self.client.table('transactions').select('*').execute()
            return response.data if response else []
        except Exception as e:
            logger.error(f"Error fetching transactions from Supabase: {str(e)}")
            return []
    
    def fetch_transactions_by_date_range(self, start_date, end_date, user_id=None):
        """Fetch transactions within a date range from Supabase"""
        try:
            query = self.client.table('transactions').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
                
            query = query.gte('date', start_date).lte('date', end_date)
            response = query.execute()
            
            return response.data if response else []
        except Exception as e:
            logger.error(f"Error fetching transactions from Supabase: {str(e)}")
            return []
            
    def fetch_accounts(self, user_id=None):
        """Fetch all accounts from Supabase"""
        try:
            if user_id:
                response = self.client.table('accounts').select('*').eq('user_id', user_id).execute()
            else:
                response = self.client.table('accounts').select('*').execute()
            return response.data if response else []
        except Exception as e:
            logger.error(f"Error fetching accounts from Supabase: {str(e)}")
            return []
    
    def store_account(self, user_id: str, account_data: Dict[str, Any]) -> Optional[str]:
        """
        Store an account in Supabase.
        
        Args:
            user_id: The ID of the user who owns the account
            account_data: Dictionary of account data
            
        Returns:
            The ID of the created/updated account, or None if failed
        """
        try:
            # Prepare record for database
            account_record = {
                'user_id': user_id,
                'account_id': account_data.get('account_id'),
                'name': account_data.get('name', 'Unnamed Account'),
                'type': account_data.get('type', 'unknown'),
                'subtype': account_data.get('subtype'),
                'current_balance': account_data.get('balances', {}).get('current'),
                'available_balance': account_data.get('balances', {}).get('available'),
                'limit': account_data.get('balances', {}).get('limit'),
                'official_name': account_data.get('official_name'),
                'mask': account_data.get('mask'),
                'institution_id': account_data.get('institution_id'),
                'institution_name': account_data.get('institution_name'),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Check for existing account to update
            existing_account = self.client.table('accounts') \
                .select('id') \
                .eq('user_id', user_id) \
                .eq('account_id', account_data.get('account_id')) \
                .execute()
                
            if existing_account.data and len(existing_account.data) > 0:
                # Update existing account
                account_db_id = existing_account.data[0]['id']
                response = self.client.table('accounts') \
                    .update(account_record) \
                    .eq('id', account_db_id) \
                    .execute()
            else:
                # Create new account
                response = self.client.table('accounts') \
                    .insert(account_record) \
                    .execute()
                    
            if response.data and len(response.data) > 0:
                account_db_id = response.data[0]['id']
                
                # If it's an investment account, store investment details
                if account_data.get('type') == 'investment':
                    self._store_investment_account_details(account_db_id, account_data)
                
                # If it's a credit account, store credit details
                if account_data.get('type') == 'credit' or account_data.get('subtype') in ['credit', 'credit card']:
                    self._store_credit_account_details(account_db_id, account_data)
                
                # If it's a loan account, store loan details
                if account_data.get('type') == 'loan' or account_data.get('subtype') in ['loan', 'mortgage']:
                    self._store_loan_account_details(account_db_id, account_data)
                    
                return account_db_id
                
            return None
        except Exception as e:
            logger.error(f"Error storing account: {str(e)}")
            return None

    def _store_investment_account_details(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """
        Store investment account details in Supabase.
        
        Args:
            account_id: The database ID of the account
            account_data: Dictionary of account data including investment details
        """
        # Check if investment record already exists
        existing = self.client.table('account_investments') \
            .select('id') \
            .eq('account_id', account_id) \
            .execute()
            
        # Prepare investment data
        investment_data = {
            'account_id': account_id,
            'total_investment_value': account_data.get('total_investment_value', 0),
            'total_cash_value': account_data.get('total_cash_value', 0),
            'total_investment_holdings': account_data.get('total_investment_holdings', 0),
            'cash_interest_rate': account_data.get('cash_interest_rate', 0),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if existing.data and len(existing.data) > 0:
            # Update existing record
            self.client.table('account_investments') \
                .update(investment_data) \
                .eq('id', existing.data[0]['id']) \
                .execute()
        else:
            # Create new record
            self.client.table('account_investments') \
                .insert(investment_data) \
                .execute()
    
    def _store_credit_account_details(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """
        Store credit account details in Supabase.
        
        Args:
            account_id: The database ID of the account
            account_data: Dictionary of account data including credit details
        """
        # Check if credit record already exists
        existing = self.client.table('account_credit_details') \
            .select('id') \
            .eq('account_id', account_id) \
            .execute()
            
        # Prepare credit data
        credit_data = {
            'account_id': account_id,
            'credit_limit': account_data.get('balances', {}).get('limit', 0),
            'current_balance': account_data.get('balances', {}).get('current', 0),
            'available_credit': account_data.get('balances', {}).get('available', 0),
            'interest_rate': account_data.get('interest_rate', 0),
            'minimum_payment': account_data.get('minimum_payment', 0),
            'payment_due_date': account_data.get('payment_due_date'),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if existing.data and len(existing.data) > 0:
            # Update existing record
            self.client.table('account_credit_details') \
                .update(credit_data) \
                .eq('id', existing.data[0]['id']) \
                .execute()
        else:
            # Create new record
            self.client.table('account_credit_details') \
                .insert(credit_data) \
                .execute()

    def _store_loan_account_details(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """
        Store loan account details in Supabase.
        
        Args:
            account_id: The database ID of the account
            account_data: Dictionary of account data including loan details
        """
        # Check if loan record already exists
        existing = self.client.table('account_loan_details') \
            .select('id') \
            .eq('account_id', account_id) \
            .execute()
            
        # Prepare loan data
        loan_data = {
            'account_id': account_id,
            'original_loan_amount': account_data.get('original_loan_amount', 0),
            'current_balance': account_data.get('balances', {}).get('current', 0),
            'interest_rate': account_data.get('interest_rate', 0),
            'minimum_payment': account_data.get('minimum_payment', 0),
            'payment_due_date': account_data.get('payment_due_date'),
            'loan_term_months': account_data.get('loan_term_months', 0),
            'loan_start_date': account_data.get('loan_start_date'),
            'loan_end_date': account_data.get('loan_end_date'),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if existing.data and len(existing.data) > 0:
            # Update existing record
            self.client.table('account_loan_details') \
                .update(loan_data) \
                .eq('id', existing.data[0]['id']) \
                .execute()
        else:
            # Create new record
            self.client.table('account_loan_details') \
                .insert(loan_data) \
                .execute()
                
    def store_security(self, security_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a security in Supabase.
        
        Args:
            security_data: Dictionary of security data
            
        Returns:
            The ID of the created/updated security, or None if failed
        """
        try:
            # Extract the security_id which we'll use to check for existing records
            security_id = security_data.get('security_id')
            if not security_id:
                logger.error("Cannot store security without security_id")
                return None
                
            # Prepare record for database
            security_record = {
                'security_id': security_id,
                'name': security_data.get('name', 'Unknown Security'),
                'ticker_symbol': security_data.get('ticker_symbol'),
                'isin': security_data.get('isin'),
                'cusip': security_data.get('cusip'),
                'type': security_data.get('type', 'unknown'),
                'close_price': security_data.get('close_price'),
                'close_price_as_of': security_data.get('close_price_as_of'),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Check for existing security to update
            existing = self.client.table('securities') \
                .select('id') \
                .eq('security_id', security_id) \
                .execute()
                
            if existing.data and len(existing.data) > 0:
                # Update existing security
                security_db_id = existing.data[0]['id']
                response = self.client.table('securities') \
                    .update(security_record) \
                    .eq('id', security_db_id) \
                    .execute()
            else:
                # Create new security
                response = self.client.table('securities') \
                    .insert(security_record) \
                    .execute()
                    
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
                
            return None
        except Exception as e:
            logger.error(f"Error storing security: {str(e)}")
            return None
            
    def store_holding(self, account_id: str, security_id: str, holding_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a holding in Supabase.
        
        Args:
            account_id: The database ID of the account
            security_id: The database ID of the security
            holding_data: Dictionary of holding data
            
        Returns:
            The ID of the created/updated holding, or None if failed
        """
        try:
            # Prepare record for database
            holding_record = {
                'account_id': account_id,
                'security_id': security_id,
                'quantity': holding_data.get('quantity', 0),
                'cost_basis': holding_data.get('cost_basis'),
                'current_value': holding_data.get('current_value', 0),
                'unrealized_pl': holding_data.get('unrealized_pl'),
                'unrealized_pl_percentage': holding_data.get('unrealized_pl_percentage'),
                'purchase_date': holding_data.get('purchase_date'),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Check for existing holding with this account/security combination
            existing = self.client.table('account_holdings') \
                .select('id') \
                .eq('account_id', account_id) \
                .eq('security_id', security_id) \
                .execute()
                
            if existing.data and len(existing.data) > 0:
                # Update existing holding
                holding_db_id = existing.data[0]['id']
                response = self.client.table('account_holdings') \
                    .update(holding_record) \
                    .eq('id', holding_db_id) \
                    .execute()
            else:
                # Create new holding
                response = self.client.table('account_holdings') \
                    .insert(holding_record) \
                    .execute()
                    
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
                
            return None
        except Exception as e:
            logger.error(f"Error storing holding: {str(e)}")
            return None
            
    def store_investment_transaction(self, account_id: str, security_id: Optional[str], transaction_data: Dict[str, Any]) -> Optional[str]:
        """
        Store investment transaction in Supabase
        
        Args:
            account_id: The Supabase account ID
            security_id: The Supabase security ID (may be None for some transaction types)
            transaction_data: Investment transaction data from Plaid
            
        Returns:
            The Supabase transaction ID if successful, None otherwise
        """
        transaction_id = transaction_data.get('investment_transaction_id')
        
        if not transaction_id:
            return None
            
        # Check if transaction already exists
        existing = self.adapter.client.table('investment_transactions') \
            .select('id') \
            .eq('transaction_id', transaction_id) \
            .execute()
            
        # Import our serialization utilities
        from .utils import serialize_for_supabase
        
        # Prepare data for storage
        transaction_record = {
            'account_id': account_id,
            'security_id': security_id,
            'transaction_id': transaction_id,
            'date': transaction_data.get('date'),
            'name': transaction_data.get('name'),
            'type': transaction_data.get('type', 'other'),
            'quantity': transaction_data.get('quantity'),
            'amount': transaction_data.get('amount', 0),
            'price': transaction_data.get('price'),
            'fees': transaction_data.get('fees')
        }
        
        # Serialize the transaction record to handle date fields and other non-JSON serializable objects
        transaction_record = serialize_for_supabase(transaction_record)
        
        # Create or update transaction
        if existing.data and len(existing.data) > 0:
            # Update existing transaction
            transaction_db_id = existing.data[0]['id']
            response = self.adapter.client.table('investment_transactions') \
                .update(transaction_record) \
                .eq('id', transaction_db_id) \
                .execute()
        else:
            # Create new transaction
            response = self.adapter.client.table('investment_transactions') \
                .insert(transaction_record) \
                .execute()
                
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
            
        return None

    def create_service_role_client(self):
        """Create a service role client with admin privileges to bypass RLS."""
        try:
            from supabase import create_client
            service_client = create_client(
                self.supabase_url,
                self.supabase_secret,  # Use service role key instead of anon key
            )
            return service_client
        except Exception as e:
            logger.error(f"Error creating service role client: {e}")
            raise e

def sync_financial_data_to_supabase(user_id):
    """
    Sync financial data to Supabase for a specific user
    This is a convenience function that can be called from various places
    """
    try:
        user = User.objects.get(id=user_id)
        adapter = SupabaseAdapter()
        
        # Sync user data
        supabase_id = SupabaseService.sync_user_to_supabase(user)
        
        if not supabase_id:
            logger.error(f"Failed to sync user {user_id} to Supabase")
            return False
        
        # Sync financial data
        # This would call specific sync methods for different data types
        
        return True
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error syncing financial data: {str(e)}")
        return False 