from django.conf import settings
from .client import SupabaseClient, get_supabase_client
from typing import Dict, Any, Optional, List
from django.contrib.auth import get_user_model
import logging
import uuid
import random
import string
from .adapter import SupabaseAdapter
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
from datetime import datetime, timedelta
from .utils import classify_account, enhanced_account_data, is_investment_account, is_retirement_account, is_credit_account, is_loan_account

User = get_user_model()
logger = logging.getLogger(__name__)

class StorageInterface:
    """
    Abstract storage interface for Plaid data.
    This allows the PlaidService to work with any storage backend.
    """
    
    def store_plaid_item(self, user_id: str, item_id: str, access_token: str, institution_id: str = None) -> Optional[str]:
        """Store a Plaid item and return its ID"""
        raise NotImplementedError("Subclasses must implement store_plaid_item")
        
    def get_plaid_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all Plaid items for a user"""
        raise NotImplementedError("Subclasses must implement get_plaid_items")
        
    def store_account(self, user_id: str, account_data: Dict[str, Any]) -> Optional[str]:
        """Store an account and return its ID"""
        raise NotImplementedError("Subclasses must implement store_account")
        
    def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get accounts for a user"""
        raise NotImplementedError("Subclasses must implement get_accounts")
        
    def store_transactions(self, transactions: List[Dict[str, Any]]) -> bool:
        """Store transactions and return success"""
        raise NotImplementedError("Subclasses must implement store_transactions")
        
    def clear_user_data(self, user_id: str) -> bool:
        """Clear all data for a specific user"""
        raise NotImplementedError("Subclasses must implement clear_user_data")


class SupabaseStorage(StorageInterface):
    """
    Supabase implementation of the storage interface.
    """
    
    def __init__(self, adapter=None):
        """Initialize with optional adapter for dependency injection"""
        # Import here to avoid circular imports
        from supabase_integration.adapter import PlaidAdapter, FinancialAdapter
        self.adapter = adapter or PlaidAdapter()
        self.financial_adapter = FinancialAdapter(self.adapter.client) if not adapter else None
        
    def store_plaid_item(self, user_id: str, item_id: str, access_token: str, institution_id: str = None) -> Optional[str]:
        """Store a Plaid item in Supabase"""
        return self.adapter.store_plaid_item(user_id, item_id, access_token, institution_id)
        
    def get_plaid_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get Plaid items from Supabase"""
        return self.adapter.get_plaid_items(user_id)
        
    def store_account(self, user_id: str, account_data: Dict[str, Any]) -> Optional[str]:
        """Store an account in Supabase"""
        return self.adapter.store_account(user_id, account_data)
        
    def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get accounts from Supabase"""
        # Import here to avoid circular imports
        if not self.financial_adapter:
            from supabase_integration.adapter import FinancialAdapter
            self.financial_adapter = FinancialAdapter(self.adapter.client)
        return self.financial_adapter.get_accounts(user_id)
        
    def store_transactions(self, transactions: List[Dict[str, Any]]) -> bool:
        """Store transactions in Supabase"""
        return self.adapter.store_transactions(transactions)
        
    def clear_user_data(self, user_id: str) -> bool:
        """Clear all Plaid-related data for a user"""
        try:
            # Get client from adapter
            client = self.adapter.client
            
            # First, get all accounts for this user
            accounts_response = client.table('accounts').select('id').eq('user_id', user_id).execute()
            
            if accounts_response.data:
                account_ids = [account['id'] for account in accounts_response.data]
                
                # Delete transactions for these accounts
                for account_id in account_ids:
                    client.table('transactions').delete().eq('account_id', account_id).execute()
                
                # Delete the accounts
                client.table('accounts').delete().eq('user_id', user_id).execute()
            
            # Delete Plaid items
            client.table('plaid_items').delete().eq('user_id', user_id).execute()
            
            logger.info(f"Cleared all Plaid data for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing user data: {str(e)}")
            return False


class PlaidService:
    """
    Service class to handle Plaid API interactions.
    Uses dependency injection for storage to decouple from specific backends.
    """
    
    def __init__(self, storage=None, use_mock_data=False):
        """
        Initialize with optional storage for dependency injection
        
        Args:
            storage: Storage implementation for data persistence
            use_mock_data: Flag to control whether mock data is generated (False by default)
        """
        self.storage = storage or SupabaseStorage()
        self.use_mock_data = use_mock_data
        logger.info(f"Initializing Plaid Service in {settings.PLAID_ENVIRONMENT} mode with mock_data={use_mock_data}")
    
    def create_link_token(self, user):
        """Create a Plaid Link token for the user"""
        try:
            # In a real implementation, this would call the Plaid API
            # For sandbox mode, we want to return a value that won't confuse
            # the Plaid SDK, which might have compatibility issues with various formats
            
            # In sandbox mode, we need to return a properly formatted link token
            # The format should be recognized by the Plaid Link SDK
            uuid_value = str(uuid.uuid4())
            # Format: link-sandbox-<random-id>
            link_token = f"link-sandbox-{uuid_value}"
            
            logger.info(f"Created sandbox link token: {link_token}")
            return link_token
        except Exception as e:
            logger.error(f"Error creating link token: {str(e)}")
            return None
    
    def exchange_public_token(self, user, public_token):
        """Exchange a public token for an access token and store it"""
        try:
            # In a real implementation, this would call the Plaid API
            # For demo purposes, we'll create a mock item and access token
            item_id = f"item_{uuid.uuid4()}"
            access_token = f"access-sandbox-{uuid.uuid4()}"
            
            # Store the Plaid item
            plaid_item_id = self.storage.store_plaid_item(
                user_id=str(user.id),
                item_id=item_id,
                access_token=access_token
            )
            
            if plaid_item_id:
                # After storing the item, sync accounts only if mock data is enabled
                if self.use_mock_data:
                    self.sync_accounts(user)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error exchanging public token: {str(e)}")
            return False
    
    def sync_accounts(self, user):
        """Sync accounts for a user from Plaid"""
        try:
            # If mock data is disabled, just return an empty list
            if not self.use_mock_data:
                logger.info("Mock data generation is disabled. No accounts synced.")
                return []
                
            # In a real implementation, this would call the Plaid API
            # For demo purposes, create some sample accounts
            logger.info("Generating mock account data")
            
            # Get all Plaid items for the user
            plaid_items = self.storage.get_plaid_items(str(user.id))
            
            accounts = []
            for item in plaid_items:
                # Create demo accounts for this item
                demo_accounts = [
                    {
                        'account_id': f"account_{uuid.uuid4()}",
                        'name': "Checking Account",
                        'type': "depository",
                        'subtype': "checking",
                        'current_balance': 2500.75,
                        'available_balance': 2300.50,
                        'institution_id': item.get('institution_id')
                    },
                    {
                        'account_id': f"account_{uuid.uuid4()}",
                        'name': "Savings Account",
                        'type': "depository",
                        'subtype': "savings",
                        'current_balance': 15000.00,
                        'available_balance': 15000.00,
                        'institution_id': item.get('institution_id')
                    },
                    {
                        'account_id': f"account_{uuid.uuid4()}",
                        'name': "Credit Card",
                        'type': "credit",
                        'subtype': "credit card",
                        'current_balance': -3250.30,
                        'available_balance': 6750.00,
                        'is_debt_account': True,
                        'debt_type': 'credit_card',
                        'institution_id': item.get('institution_id')
                    }
                ]
                
                for account_data in demo_accounts:
                    # Store the account
                    account_id = self.storage.store_account(str(user.id), account_data)
                    if account_id:
                        accounts.append(account_data)
            
            return accounts
        except Exception as e:
            logger.error(f"Error syncing accounts: {str(e)}")
            return []
    
    def sync_transactions(self, user, start_date, end_date):
        """Sync transactions for a user from Plaid"""
        try:
            # If mock data is disabled, just return an empty list
            if not self.use_mock_data:
                logger.info("Mock data generation is disabled. No transactions synced.")
                return []
                
            logger.info("Generating mock transaction data")
            
            # Get the user's accounts to create transactions for
            accounts = self.storage.get_accounts(str(user.id))
            
            if not accounts:
                return []
            
            all_transactions = []
            
            # Generate random transactions for each account
            for account in accounts:
                # Create 5-10 transactions per account
                num_transactions = random.randint(5, 10)
                for i in range(num_transactions):
                    # Create a random date between start_date and end_date
                    days_range = (end_date - start_date).days
                    random_days = random.randint(0, max(0, days_range))
                    tx_date = start_date + timedelta(days=random_days)
                    
                    # Generate transaction data
                    tx_data = {
                        'account_id': account['id'],
                        'transaction_id': f"tx_{uuid.uuid4()}",
                        'amount': round(random.uniform(5, 500), 2),
                        'date': tx_date,
                        'merchant_name': f"Merchant {i+1}",
                        'category': random.choice(['Food', 'Shopping', 'Transportation', 'Entertainment']),
                        'pending': random.choice([True, False, False, False])  # 25% chance of pending
                    }
                    
                    all_transactions.append(tx_data)
            
            # Store all transactions
            if all_transactions:
                self.storage.store_transactions(all_transactions)
            
            return all_transactions
        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            return []
    
    def refresh_accounts(self, user):
        """Refresh accounts for a user"""
        return self.sync_accounts(user)
    
    def refresh_transactions(self, user, start_date, end_date):
        """Refresh transactions for a user"""
        return self.sync_transactions(user, start_date, end_date)
        
    def clear_user_data(self, user):
        """Clear all Plaid-related data for a user"""
        try:
            success = self.storage.clear_user_data(str(user.id))
            if success:
                logger.info(f"Successfully cleared Plaid data for user {user.id}")
            else:
                logger.warning(f"Failed to clear Plaid data for user {user.id}")
            return success
        except Exception as e:
            logger.error(f"Error clearing user data: {str(e)}")
            return False

class SupabaseService:
    """
    Service class to handle Supabase operations.
    This is a higher-level service that builds on the adapter.
    """
    
    @staticmethod
    def sync_user_to_supabase(user):
        """
        Sync a Django user to Supabase
        """
        try:
            logger.info(f"Syncing user {user.email} to Supabase")
            adapter = SupabaseAdapter()
            
            # Check if the user already exists in Supabase
            supabase_user = adapter.get_user_by_email(user.email)
            
            if supabase_user:
                # User exists in Supabase, update profile
                user_id = supabase_user['id']
                
                # Only update the email - other profile fields should be updated via the profile form
                # This follows the actual profile schema in the database
                profile_data = {
                    'id': user_id,
                    'email': user.email,
                }
                logger.info(f"Updating existing Supabase user with data: {profile_data}")
                adapter.update_profile(user_id, profile_data)
                
                # Store the mapping in Django's session or cache if needed
                # No need for SupabaseSync model anymore
                
                return user_id
            else:
                # User doesn't exist in Supabase, create them
                # Generate a random password for the Supabase user
                password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
                
                user_id = adapter.create_user(user.email, password)
                
                if user_id:
                    # The profile should already be created by the database trigger
                    # We just need to ensure the email is consistent
                    profile_data = {
                        'id': user_id,
                        'email': user.email,
                    }
                    logger.info(f"Updating new Supabase user with data: {profile_data}")
                    adapter.update_profile(user_id, profile_data)
                    
                    return user_id
                else:
                    # Failed to create user
                    logger.error(f"Failed to create user in Supabase: {user.email}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error syncing user to Supabase: {str(e)}")
            logger.error(f"Error details: {repr(e)}")
            return None
            
    @staticmethod
    def get_supabase_id_for_user(user):
        """Get the Supabase ID for a Django user"""
        try:
            # Get user ID directly from Supabase using email
            adapter = SupabaseAdapter()
            supabase_user = adapter.get_user_by_email(user.email)
            if supabase_user:
                return supabase_user['id']
            return None
        except Exception as e:
            logger.error(f"Error getting Supabase ID for user: {str(e)}")
            return None

    def __init__(self):
        self.adapter = SupabaseAdapter()
    
    def store_account(self, user_id: str, account_data: Dict[str, Any]) -> Optional[str]:
        """
        Store account information in Supabase
        
        Args:
            user_id: The user's ID in Supabase
            account_data: Account data from Plaid
            
        Returns:
            The Supabase account ID if successful, None otherwise
        """
        # Check if account already exists
        account_id = account_data.get('account_id')
        
        if not account_id:
            return None
            
        existing_account = self.adapter.client.table('accounts') \
            .select('id') \
            .eq('user_id', user_id) \
            .eq('account_id', account_id) \
            .execute()
            
        # Enhance account data with categorization
        enhanced = enhanced_account_data(account_data)
        
        # Prepare data for storage
        account_record = {
            'user_id': user_id,
            'institution_id': enhanced.get('institution_id'),
            'account_id': enhanced.get('account_id'),
            'name': enhanced.get('name'),
            'type': enhanced.get('type'),
            'subtype': enhanced.get('subtype', ''),
            'account_category': enhanced.get('account_category'),
            'current_balance': enhanced.get('balances', {}).get('current', 0),
            'available_balance': enhanced.get('balances', {}).get('available', 0),
            'mask': enhanced.get('mask', ''),
            'official_name': enhanced.get('official_name', ''),
            'currency_code': enhanced.get('currency_code', 'USD')
        }
        
        # Create or update account
        if existing_account.data and len(existing_account.data) > 0:
            # Update existing account
            account_db_id = existing_account.data[0]['id']
            response = self.adapter.client.table('accounts') \
                .update(account_record) \
                .eq('id', account_db_id) \
                .execute()
        else:
            # Create new account
            response = self.adapter.client.table('accounts') \
                .insert(account_record) \
                .execute()
        
        if response.data and len(response.data) > 0:
            account_db_id = response.data[0]['id']
            
            # Store account-type specific details
            if is_investment_account(account_data):
                self._store_investment_account_details(account_db_id, account_data)
            elif is_credit_account(account_data):
                self._store_credit_account_details(account_db_id, account_data)
            elif is_loan_account(account_data):
                self._store_loan_account_details(account_db_id, account_data)
                
            return account_db_id
            
        return None
        
    def _store_investment_account_details(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """
        Store investment account specific details
        
        Args:
            account_id: The Supabase account ID
            account_data: Account data from Plaid
        """
        # Check if investment record already exists
        existing = self.adapter.client.table('account_investments') \
            .select('id') \
            .eq('account_id', account_id) \
            .execute()
            
        # Extract investment-specific data
        is_retirement = is_retirement_account(account_data)
        
        investment_data = {
            'account_id': account_id,
            'retirement_account': is_retirement
        }
        
        # Optional fields
        if 'ytd_contributions' in account_data:
            investment_data['contribution_ytd'] = account_data['ytd_contributions']
            
        if 'ytd_dividend_income' in account_data:
            investment_data['ytd_dividend_income'] = account_data['ytd_dividend_income']
            
        if 'ytd_interest_paid' in account_data:
            investment_data['ytd_interest_paid'] = account_data['ytd_interest_paid']
            
        if 'ytd_fees' in account_data:
            investment_data['total_fees_ytd'] = account_data['ytd_fees']
        
        # Create or update investment account details
        if existing.data and len(existing.data) > 0:
            # Update existing record
            self.adapter.client.table('account_investments') \
                .update(investment_data) \
                .eq('id', existing.data[0]['id']) \
                .execute()
        else:
            # Create new record
            self.adapter.client.table('account_investments') \
                .insert(investment_data) \
                .execute()
                
    def _store_credit_account_details(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """
        Store credit account specific details
        
        Args:
            account_id: The Supabase account ID
            account_data: Account data from Plaid
        """
        # Check if credit record already exists
        existing = self.adapter.client.table('account_credit_details') \
            .select('id') \
            .eq('account_id', account_id) \
            .execute()
            
        # Extract credit-specific data
        credit_data = {
            'account_id': account_id
        }
        
        # Optional fields from Plaid credit data
        if 'credit_info' in account_data:
            info = account_data['credit_info']
            
            if 'is_overdue' in info:
                credit_data['is_overdue'] = info['is_overdue']
                
            if 'last_payment_amount' in info:
                credit_data['last_payment_amount'] = info['last_payment_amount']
                
            if 'last_payment_date' in info:
                credit_data['last_payment_date'] = info['last_payment_date']
                
            if 'last_statement_date' in info:
                credit_data['last_statement_date'] = info['last_statement_date']
                
            if 'last_statement_balance' in info:
                credit_data['last_statement_balance'] = info['last_statement_balance']
                
            if 'minimum_payment' in info:
                credit_data['minimum_payment'] = info['minimum_payment']
                
            if 'next_payment_due_date' in info:
                credit_data['next_payment_due_date'] = info['next_payment_due_date']
                
            if 'interest_rate' in info:
                credit_data['interest_rate'] = info['interest_rate']
                
            if 'credit_limit' in info:
                credit_data['credit_limit'] = info['credit_limit']
        
        # Create or update credit account details
        if existing.data and len(existing.data) > 0:
            # Update existing record
            self.adapter.client.table('account_credit_details') \
                .update(credit_data) \
                .eq('id', existing.data[0]['id']) \
                .execute()
        else:
            # Create new record
            self.adapter.client.table('account_credit_details') \
                .insert(credit_data) \
                .execute()
                
    def _store_loan_account_details(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """
        Store loan account specific details
        
        Args:
            account_id: The Supabase account ID
            account_data: Account data from Plaid
        """
        # Check if loan record already exists
        existing = self.adapter.client.table('account_loan_details') \
            .select('id') \
            .eq('account_id', account_id) \
            .execute()
            
        # Extract loan-specific data
        loan_data = {
            'account_id': account_id
        }
        
        # Optional fields from Plaid loan data
        if 'loan_info' in account_data:
            info = account_data['loan_info']
            
            if 'origination_date' in info:
                loan_data['origination_date'] = info['origination_date']
                
            if 'origination_principal' in info:
                loan_data['origination_principal'] = info['origination_principal']
                
            if 'interest_rate' in info:
                loan_data['interest_rate'] = info['interest_rate']
                
            if 'interest_rate_type' in info:
                loan_data['interest_rate_type'] = info['interest_rate_type']
                
            if 'maturity_date' in info:
                loan_data['maturity_date'] = info['maturity_date']
                
            if 'loan_term' in info:
                loan_data['loan_term'] = info['loan_term']
                
            if 'payment_amount' in info:
                loan_data['payment_amount'] = info['payment_amount']
                
            if 'payment_frequency' in info:
                loan_data['payment_frequency'] = info['payment_frequency']
                
            if 'next_payment_due_date' in info:
                loan_data['next_payment_due_date'] = info['next_payment_due_date']
                
            if 'ytd_interest_paid' in info:
                loan_data['ytd_interest_paid'] = info['ytd_interest_paid']
                
            if 'ytd_principal_paid' in info:
                loan_data['ytd_principal_paid'] = info['ytd_principal_paid']
        
        # Create or update loan account details
        if existing.data and len(existing.data) > 0:
            # Update existing record
            self.adapter.client.table('account_loan_details') \
                .update(loan_data) \
                .eq('id', existing.data[0]['id']) \
                .execute()
        else:
            # Create new record
            self.adapter.client.table('account_loan_details') \
                .insert(loan_data) \
                .execute()
                
    def store_security(self, security_data: Dict[str, Any]) -> Optional[str]:
        """
        Store security information in Supabase
        
        Args:
            security_data: Security data from Plaid
            
        Returns:
            The Supabase security ID if successful, None otherwise
        """
        security_id = security_data.get('security_id')
        
        if not security_id:
            return None
            
        # Check if security already exists
        existing = self.adapter.client.table('securities') \
            .select('id') \
            .eq('security_id', security_id) \
            .execute()
            
        # Prepare data for storage
        security_record = {
            'security_id': security_id,
            'name': security_data.get('name', 'Unknown Security'),
            'ticker_symbol': security_data.get('ticker_symbol'),
            'isin': security_data.get('isin'),
            'cusip': security_data.get('cusip'),
            'type': security_data.get('type'),
            'close_price': security_data.get('close_price'),
            'close_price_as_of': security_data.get('close_price_as_of'),
            'currency_code': security_data.get('iso_currency_code', 'USD')
        }
        
        # Create or update security
        if existing.data and len(existing.data) > 0:
            # Update existing security
            security_db_id = existing.data[0]['id']
            response = self.adapter.client.table('securities') \
                .update(security_record) \
                .eq('id', security_db_id) \
                .execute()
        else:
            # Create new security
            response = self.adapter.client.table('securities') \
                .insert(security_record) \
                .execute()
                
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
            
        return None
        
    def store_holding(self, account_id: str, security_id: str, holding_data: Dict[str, Any]) -> Optional[str]:
        """
        Store holding (position) information in Supabase
        
        Args:
            account_id: The Supabase account ID
            security_id: The Supabase security ID
            holding_data: Holding data from Plaid
            
        Returns:
            The Supabase holding ID if successful, None otherwise
        """
        # Check for existing holding with this account/security combination
        existing = self.adapter.client.table('account_holdings') \
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
            'institution_price': holding_data.get('institution_price'),
            'institution_price_as_of': holding_data.get('institution_price_as_of')
        }
        
        # Create or update holding
        if existing.data and len(existing.data) > 0:
            # Update existing holding
            holding_db_id = existing.data[0]['id']
            response = self.adapter.client.table('account_holdings') \
                .update(holding_record) \
                .eq('id', holding_db_id) \
                .execute()
        else:
            # Create new holding
            response = self.adapter.client.table('account_holdings') \
                .insert(holding_record) \
                .execute()
                
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
            
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