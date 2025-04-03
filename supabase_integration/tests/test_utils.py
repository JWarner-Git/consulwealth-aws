import unittest
import datetime
import uuid
from ..utils import serialize_for_supabase, serialize_value, clean_for_schema, extract_schema_columns

class TestSerializationUtils(unittest.TestCase):
    """Test the serialization utilities for Supabase data."""
    
    def test_serialize_value_date(self):
        """Test serializing date objects."""
        date_obj = datetime.date(2025, 4, 1)
        result = serialize_value(date_obj)
        self.assertEqual(result, "2025-04-01")
    
    def test_serialize_value_datetime(self):
        """Test serializing datetime objects."""
        datetime_obj = datetime.datetime(2025, 4, 1, 13, 48, 25)
        result = serialize_value(datetime_obj)
        self.assertTrue(result.startswith("2025-04-01T13:48:25"))
    
    def test_serialize_value_uuid(self):
        """Test serializing UUID objects."""
        uuid_obj = uuid.UUID("65c33222-de65-4c56-ab96-c5aa9a678709")
        result = serialize_value(uuid_obj)
        self.assertEqual(result, "65c33222-de65-4c56-ab96-c5aa9a678709")
    
    def test_serialize_value_nested_dict(self):
        """Test serializing nested dictionaries with date objects."""
        nested_dict = {
            "outer_key": {
                "inner_date": datetime.date(2025, 4, 1)
            }
        }
        result = serialize_value(nested_dict)
        self.assertEqual(result, {"outer_key": {"inner_date": "2025-04-01"}})
    
    def test_serialize_value_list(self):
        """Test serializing lists with various objects."""
        test_list = [
            datetime.date(2025, 4, 1),
            {"date": datetime.date(2025, 4, 2)},
            uuid.UUID("65c33222-de65-4c56-ab96-c5aa9a678709")
        ]
        result = serialize_value(test_list)
        self.assertEqual(result, [
            "2025-04-01",
            {"date": "2025-04-02"},
            "65c33222-de65-4c56-ab96-c5aa9a678709"
        ])
    
    def test_serialize_for_supabase_complex_object(self):
        """Test serializing a complex transaction object."""
        transaction = {
            "id": uuid.UUID("65c33222-de65-4c56-ab96-c5aa9a678709"),
            "date": datetime.date(2025, 4, 1),
            "authorized_date": datetime.date(2025, 3, 31),
            "amount": 100.50,
            "merchant_name": "Test Merchant",
            "metadata": {
                "created_at": datetime.datetime(2025, 4, 1, 13, 48, 25),
                "tags": ["test", "transaction"]
            }
        }
        result = serialize_for_supabase(transaction)
        
        self.assertEqual(result["id"], "65c33222-de65-4c56-ab96-c5aa9a678709")
        self.assertEqual(result["date"], "2025-04-01")
        self.assertEqual(result["authorized_date"], "2025-03-31")
        self.assertEqual(result["amount"], 100.50)
        self.assertEqual(result["merchant_name"], "Test Merchant")
        self.assertTrue(result["metadata"]["created_at"].startswith("2025-04-01T13:48:25"))
        self.assertEqual(result["metadata"]["tags"], ["test", "transaction"])
    
    def test_clean_for_schema(self):
        """Test cleaning and serializing data according to a schema."""
        data = {
            "id": uuid.UUID("65c33222-de65-4c56-ab96-c5aa9a678709"),
            "date": datetime.date(2025, 4, 1),
            "amount": 100.50,
            "merchant_name": "Test Merchant",
            "extra_field": "This should be excluded"
        }
        schema_columns = ["id", "date", "amount", "merchant_name"]
        
        result = clean_for_schema(data, schema_columns)
        
        self.assertEqual(len(result), 4)
        self.assertEqual(result["id"], "65c33222-de65-4c56-ab96-c5aa9a678709")
        self.assertEqual(result["date"], "2025-04-01")
        self.assertEqual(result["amount"], 100.50)
        self.assertEqual(result["merchant_name"], "Test Merchant")
        self.assertNotIn("extra_field", result)

if __name__ == "__main__":
    unittest.main() 