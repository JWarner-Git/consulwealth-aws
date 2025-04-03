#!/usr/bin/env python
"""
Test script to verify the transaction storage with date objects.
This simulates the transaction syncing process with test data containing date objects.
"""

import os
import sys
import datetime
import uuid
import logging

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clean_backend.settings")
import django
django.setup()

from supabase_integration.adapter import PlaidAdapter
from supabase_integration.utils import serialize_for_supabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_transaction_storage():
    """Test storing transactions with date objects"""
    # Create a sample transaction with date objects
    transactions = [
        {
            'id': str(uuid.uuid4()),
            'account_id': '38fe61d3-2ab3-41dd-85b4-8901bb88403f',  # Sample account ID
            'transaction_id': f'test_tx_{uuid.uuid4()}',
            'amount': 123.45,
            'date': datetime.date.today(),  # This was causing the error
            'authorized_date': datetime.date.today() - datetime.timedelta(days=1),
            'name': 'Test Transaction',
            'merchant_name': 'Test Merchant',
            'category': 'Test Category',
            'pending': False,
        },
        {
            'id': str(uuid.uuid4()),
            'account_id': '7cb30b7d-2d4f-44b2-b5b2-5d19a2264522',  # Sample account ID
            'transaction_id': f'test_tx_{uuid.uuid4()}',
            'amount': 67.89,
            'date': datetime.date.today() - datetime.timedelta(days=2),  # This was causing the error
            'authorized_date': datetime.date.today() - datetime.timedelta(days=3),
            'name': 'Another Test Transaction',
            'merchant_name': 'Another Test Merchant',
            'category': 'Another Test Category',
            'pending': True,
        }
    ]
    
    logger.info(f"Created {len(transactions)} test transactions with date objects")
    
    # Initialize the adapter
    adapter = PlaidAdapter()
    
    # Try storing the transactions
    try:
        logger.info("Attempting to store transactions with date objects")
        success = adapter.store_transactions(transactions)
        if success:
            logger.info("Successfully stored transactions with date objects")
        else:
            logger.error("Failed to store transactions")
    except Exception as e:
        logger.error(f"Error storing transactions: {str(e)}")
        raise

if __name__ == "__main__":
    test_transaction_storage() 