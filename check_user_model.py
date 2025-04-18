import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Import the User model
from django.contrib.auth import get_user_model
User = get_user_model()

# Get the model fields
fields = User._meta.get_fields()

# Print field information
print(f"Fields for {User.__name__} model:")
for field in fields:
    print(f"- {field.name} ({field.__class__.__name__})")

# Check specifically for last_supabase_validation field
has_validation_field = hasattr(User, 'last_supabase_validation')
print(f"\nHas last_supabase_validation field: {has_validation_field}")

# Check the database schema
from django.db import connection
cursor = connection.cursor()
table_name = User._meta.db_table
cursor.execute(f"PRAGMA table_info({table_name});")
columns = cursor.fetchall()

print(f"\nDatabase columns for {table_name} table:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# Check if the table has the last_supabase_validation column
has_db_field = any(col[1] == 'last_supabase_validation' for col in columns)
print(f"\nDatabase has last_supabase_validation column: {has_db_field}")

if has_validation_field and not has_db_field:
    print("\nThe field exists in the model but not in the database.")
    print("You need to create and apply a migration for this field.") 