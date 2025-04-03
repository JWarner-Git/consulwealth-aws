import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Import the User model
from django.contrib.auth import get_user_model
User = get_user_model()

# Get all tables
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Database tables:")
for table in tables:
    print(f"- {table[0]}")

# Check if the users_user table exists
user_table = User._meta.db_table
print(f"\nLooking for user table: {user_table}")
has_table = any(table[0] == user_table for table in tables)
print(f"Table exists: {has_table}")

if has_table:
    # Check columns in the users_user table
    cursor.execute(f"PRAGMA table_info({user_table});")
    columns = cursor.fetchall()
    print(f"\nColumns in {user_table} table:")
    for col in columns:
        print(f"- {col[1]} ({col[2]})")
        
    # Check if the last_supabase_validation column exists
    has_validation_field = any(col[1] == 'last_supabase_validation' for col in columns)
    print(f"\nTable has last_supabase_validation column: {has_validation_field}")
else:
    print("\nUser table does not exist. We need to create it.")
    print("Try running: python manage.py migrate --no-input") 