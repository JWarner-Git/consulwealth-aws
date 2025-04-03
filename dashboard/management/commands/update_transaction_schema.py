"""
Management command to update the transactions table schema in Supabase.
This command will add missing fields needed for Plaid transaction data.
"""
import logging
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from supabase import create_client

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update the transactions table schema in Supabase to support Plaid fields'

    def handle(self, *args, **options):
        # Initialize Supabase client
        supabase_url = settings.SUPABASE_URL
        supabase_key = settings.SUPABASE_SERVICE_KEY
        
        self.stdout.write("Initializing Supabase client...")
        try:
            if not supabase_url or not supabase_key:
                self.stdout.write(self.style.ERROR("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in settings"))
                return
                
            # We need to use the service key for schema modifications
            client = create_client(supabase_url, supabase_key)
            
            # Load the SQL migration file
            migration_path = os.path.join(
                settings.BASE_DIR, 
                'migration_add_plaid_transaction_fields.sql'
            )
            
            self.stdout.write(f"Loading migration from {migration_path}")
            
            if not os.path.exists(migration_path):
                self.stdout.write(self.style.ERROR(f"Migration file not found: {migration_path}"))
                return
                
            with open(migration_path, 'r') as file:
                migration_sql = file.read()
                
            self.stdout.write("Running migration on Supabase...")
            
            # Execute the migration as a single SQL script
            # Use direct SQL access because Supabase Python client doesn't expose schema operations
            # This requires the service key with enough permissions
            response = client.rpc('exec_sql', {'sql': migration_sql}).execute()
            
            if response.data is None:
                self.stdout.write(self.style.SUCCESS("Successfully updated transactions schema"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Schema update completed: {response.data}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error updating schema: {str(e)}"))
            logger.exception("Full exception details:")
            return 