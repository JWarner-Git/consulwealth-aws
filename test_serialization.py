#!/usr/bin/env python
"""
Test script to verify the date serialization utilities without Django.
"""

import sys
import json
import datetime
import uuid

print("Python path:", sys.path)

try:
    # Import our serialization utilities directly
    print("Attempting to import serialization utilities...")
    from supabase_integration.utils import serialize_for_supabase, serialize_value
    print("Successfully imported serialization utilities")
except ImportError as e:
    print("Error importing serialization utilities:", e)
    sys.exit(1)

def test_serialization():
    """Test serializing objects with date fields"""
    print("Testing date serialization for JSON...")
    
    # Create sample transaction data with date objects
    transaction = {
        'id': uuid.uuid4(),
        'account_id': '38fe61d3-2ab3-41dd-85b4-8901bb88403f', 
        'transaction_id': f'test_tx_{uuid.uuid4()}',
        'amount': 123.45,
        'date': datetime.date.today(),  # This was causing the error
        'authorized_date': datetime.date.today() - datetime.timedelta(days=1),
        'name': 'Test Transaction',
        'merchant_name': 'Test Merchant',
        'category': 'Test Category',
        'pending': False,
    }
    
    print(f"Created test transaction with date field: {transaction['date']}")
    
    # Try serializing to JSON directly (this would fail without our utilities)
    try:
        json_str = json.dumps(transaction)
        print("❌ Failed test: Date object serialized without error (but it should fail)")
    except TypeError as e:
        print(f"✅ Expected error with direct serialization: {e}")
    
    # Now use our serialization utility
    print("Serializing with our utility...")
    serialized_transaction = serialize_for_supabase(transaction)
    print(f"Serialized date: {serialized_transaction.get('date')}")
    print(f"Serialized authorized_date: {serialized_transaction.get('authorized_date')}")
    
    # Now try to serialize to JSON
    try:
        json_str = json.dumps(serialized_transaction)
        print(f"✅ Successfully serialized to JSON with our utility")
        print(f"JSON: {json_str[:100]}...")
    except TypeError as e:
        print(f"❌ Unexpected error with our serialization: {e}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_serialization() 