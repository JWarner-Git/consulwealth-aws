import os
import django
import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Get a cursor to execute raw SQL
from django.db import connection
cursor = connection.cursor()

# Check if the migration already exists
cursor.execute("SELECT id FROM django_migrations WHERE app='users' AND name='0001_initial'")
if not cursor.fetchone():
    # Insert the migration record - using %s placeholders which Django will convert appropriately
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
        ['users', '0001_initial', datetime.datetime.now()]
    )
    print("Successfully added users.0001_initial to the migration history.")
else:
    print("Migration users.0001_initial is already in the history.")

# Commit the transaction
connection.commit() 