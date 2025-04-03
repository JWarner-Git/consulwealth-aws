"""
Utility functions for the Supabase integration.
"""
from typing import Dict, Any, List, Optional, Union
import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)

def classify_account(account: Dict[str, Any]) -> str:
    """
    Classify a Plaid account into a standardized category.
    
    This is a central utility that should be used throughout the application
    to ensure consistent categorization of accounts.
    
    Args:
        account: A dictionary containing Plaid account data
        
    Returns:
        A string representing the account category:
        - 'investment' - Any investment or retirement account
        - 'depository' - Checking, savings, etc.
        - 'credit' - Credit cards and lines of credit
        - 'loan' - Loans, mortgages, etc.
        - 'other' - Any other account type
    """
    try:
        # Safely get account data with defaults
        account_type = str(account.get('type', '')).lower() if isinstance(account, dict) else ''
        account_subtype = str(account.get('subtype', '')).lower() if isinstance(account, dict) else ''
        account_name = str(account.get('name', '')).lower() if isinstance(account, dict) else ''
        
        # Investment accounts detection (comprehensive)
        investment_types = ['investment', 'retirement', 'brokerage', 'cash management', '401k', 'ira', 'roth', '403b']
        
        # Check if account type, subtype, or name contains investment-related terms
        if (any(inv_type in account_type for inv_type in investment_types) or
            any(inv_type in account_subtype for inv_type in investment_types) or
            any(inv_type in account_name for inv_type in ['investment', 'brokerage', 'retirement', '401k', 'ira'])):
            return 'investment'
        
        # For other account types, use standard Plaid categorization
        if account_type in ['depository', 'credit', 'loan']:
            return account_type
    except Exception as e:
        logger.error(f"Error classifying account: {str(e)}")
    
    # If we can't categorize it clearly, mark as 'other'
    return 'other'

def is_investment_account(account: Dict[str, Any]) -> bool:
    """
    Check if an account is an investment account based on Plaid type/subtype
    
    Args:
        account: A dictionary containing Plaid account data
        
    Returns:
        bool: True if it's an investment account, False otherwise
    """
    try:
        # Handle both dictionary and Plaid API object
        if not isinstance(account, dict):
            if hasattr(account, 'to_dict'):
                account = account.to_dict()
            elif hasattr(account, '__dict__'):
                account = account.__dict__
                
        # Check the most obvious classification first
        if account.get('type') == 'investment':
            return True
            
        # Types that are definitely investments
        investment_types = ['investment', 'brokerage', 'retirement']
        
        # Subtypes that are investments regardless of type
        investment_subtypes = [
            '401k', '403b', '457b', 'ira', 'roth', 'roth ira', 'traditional ira',
            'sep ira', 'simple ira', 'brokerage', 'education savings account',
            'health reimbursement arrangement', 'hsa', 'non-taxable brokerage account',
            'pension', 'plan', 'retirement', 'thrift savings plan', 'trust', 'ugma', 'utma',
            'variable annuity', 'mutual fund', 'fixed annuity', 'annuity'
        ]
        
        # Check if this account explicitly has the is_investment flag
        if account.get('is_investment') or account.get('is_investment_account'):
            return True
            
        # Check type
        account_type = account.get('type', '').lower()
        if account_type in investment_types:
            return True
            
        # Check subtype (could be either 'subtype' or 'account_subtype' field)
        account_subtype = account.get('subtype', account.get('account_subtype', '')).lower()
        if account_subtype in investment_subtypes:
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error in is_investment_account: {str(e)}")
        return False

def is_retirement_account(account: Dict[str, Any]) -> bool:
    """
    Check if an account is specifically a retirement account.
    
    Args:
        account: A dictionary containing Plaid account data
        
    Returns:
        True if the account is a retirement account, False otherwise
    """
    try:
        # Safely get account data with defaults
        account_type = str(account.get('type', '')).lower() if isinstance(account, dict) else ''
        account_subtype = str(account.get('subtype', '')).lower() if isinstance(account, dict) else ''
        account_name = str(account.get('name', '')).lower() if isinstance(account, dict) else ''
        
        retirement_indicators = ['retirement', '401k', 'ira', 'roth', '403b', 'pension']
        
        return (
            'retirement' in account_type or
            any(ind in account_subtype for ind in retirement_indicators) or
            any(ind in account_name for ind in retirement_indicators)
        )
    except Exception:
        # Default to False if any error occurs
        return False

def is_credit_account(account: Dict[str, Any]) -> bool:
    """
    Check if an account is a credit account.
    
    Args:
        account: A dictionary containing Plaid account data
        
    Returns:
        True if the account is a credit account, False otherwise
    """
    try:
        return classify_account(account) == 'credit'
    except Exception:
        # Default to False if any error occurs
        return False

def is_loan_account(account: Dict[str, Any]) -> bool:
    """
    Check if an account is a loan account.
    
    Args:
        account: A dictionary containing Plaid account data
        
    Returns:
        True if the account is a loan account, False otherwise
    """
    try:
        return classify_account(account) == 'loan'
    except Exception:
        # Default to False if any error occurs
        return False

def enhanced_account_data(account: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Plaid account and enhance it with additional categorization data.
    Use this when storing accounts in the database to ensure proper categorization.
    
    Args:
        account: A dictionary or object containing Plaid account data
        
    Returns:
        A dictionary with enhanced account data including the standardized category
    """
    try:
        # First try to convert to dictionary if it's not already one
        if not isinstance(account, dict):
            if hasattr(account, 'to_dict'):
                account_dict = account.to_dict()
            elif hasattr(account, '__dict__'):
                account_dict = {k: v for k, v in account.__dict__.items() if not k.startswith('_')}
            else:
                # If we can't convert, create an empty dict and log error
                logger.error(f"Could not convert account object to dictionary: {type(account)}")
                account_dict = {}
        else:
            account_dict = account
            
        # Create a fresh dictionary with the data we need
        enhanced = {}
        
        # Copy standard fields
        for field in ['account_id', 'name', 'official_name', 'type', 'subtype', 'mask', 'institution_id']:
            if field in account_dict:
                enhanced[field] = account_dict.get(field)
        
        # Get balances
        balances = account_dict.get('balances', {})
        if balances:
            if isinstance(balances, dict):
                enhanced['current_balance'] = balances.get('current')
                enhanced['available_balance'] = balances.get('available')
                enhanced['limit'] = balances.get('limit')
                enhanced['iso_currency_code'] = balances.get('iso_currency_code')
            else:
                # Handle case where balances is a Plaid API object
                if hasattr(balances, 'current'):
                    enhanced['current_balance'] = getattr(balances, 'current')
                if hasattr(balances, 'available'):
                    enhanced['available_balance'] = getattr(balances, 'available')
                if hasattr(balances, 'limit'):
                    enhanced['limit'] = getattr(balances, 'limit')
                if hasattr(balances, 'iso_currency_code'):
                    enhanced['iso_currency_code'] = getattr(balances, 'iso_currency_code')
        
        # Check if this is an investment account
        enhanced['is_investment'] = is_investment_account(account_dict)
        enhanced['is_investment_account'] = enhanced['is_investment']
            
        # Check if this is a credit account
        enhanced['is_credit'] = is_credit_account(account_dict)
            
        # Check if this is a loan account
        enhanced['is_loan'] = is_loan_account(account_dict)
            
        # Check if this is a depository account
        enhanced['is_depository'] = (
            account_dict.get('type') == 'depository' or 
            account_dict.get('type') == 'checking' or
            account_dict.get('type') == 'savings'
        )
        
        # We no longer add UI enhancements directly to the database
        # This avoids schema issues if those columns don't exist
        # The UI colors and icons should be handled by the frontend instead
        
        return enhanced
    except Exception as e:
        logger.error(f"Error in enhanced_account_data: {str(e)}")
        return {}

def serialize_for_supabase(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Recursively serialize data for Supabase, handling Python objects that aren't JSON serializable.
    
    Args:
        data: A dictionary or list of dictionaries to serialize
        
    Returns:
        The serialized data ready for Supabase
    """
    if isinstance(data, list):
        return [serialize_for_supabase(item) for item in data]
    
    if not isinstance(data, dict):
        return data
    
    serialized_data = {}
    for key, value in data.items():
        serialized_data[key] = serialize_value(value)
    
    return serialized_data

def serialize_value(value: Any) -> Any:
    """
    Serialize a single value for Supabase
    
    Args:
        value: The value to serialize
        
    Returns:
        The serialized value
    """
    # Handle None
    if value is None:
        return None
    
    # Handle date and datetime
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    
    # Handle UUID
    if isinstance(value, uuid.UUID):
        return str(value)
    
    # Handle lists and dictionaries recursively
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    
    # Handle other types
    return value

def clean_for_schema(data: Dict[str, Any], schema_columns: List[str]) -> Dict[str, Any]:
    """
    Clean data to match schema columns and ensure all values are serialized
    
    Args:
        data: The data to clean
        schema_columns: List of column names in the schema
        
    Returns:
        Cleaned and serialized data
    """
    # First serialize all values
    serialized_data = serialize_for_supabase(data)
    
    # Then filter to only include fields in the schema
    return {k: v for k, v in serialized_data.items() if k in schema_columns}

def extract_schema_columns(response) -> List[str]:
    """
    Extract column names from a Supabase response
    
    Args:
        response: The Supabase response
        
    Returns:
        List of column names
    """
    try:
        if hasattr(response, 'columns') and response.columns:
            return [col.name for col in response.columns]
    except Exception as e:
        logger.warning(f"Could not extract schema columns: {str(e)}")
    
    return [] 