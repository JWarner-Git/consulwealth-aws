import os
from django.core.management.base import BaseCommand
from supabase_integration.client import get_supabase_client

class Command(BaseCommand):
    help = 'Apply SQL migrations to Supabase'

    def handle(self, *args, **options):
        self.stdout.write('Applying Supabase migrations...')
        
        supabase = get_supabase_client()
        
        # Get all migration files from the migrations directory
        migrations_dir = os.path.join(os.path.dirname(__file__), '../../migrations')
        
        if not os.path.exists(migrations_dir):
            self.stdout.write(self.style.ERROR(f'Migrations directory not found: {migrations_dir}'))
            return
        
        # Get all SQL files in the migrations directory
        migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.sql')]
        
        if not migration_files:
            self.stdout.write(self.style.WARNING('No migration files found'))
            return
        
        self.stdout.write(f'Found {len(migration_files)} migration files')
        
        # Apply each migration
        for migration_file in migration_files:
            file_path = os.path.join(migrations_dir, migration_file)
            self.stdout.write(f'Applying migration: {migration_file}')
            
            try:
                # Read the SQL file
                with open(file_path, 'r') as f:
                    sql = f.read()
                
                # Execute the SQL on Supabase
                result = supabase.rpc('pg_extensions', {'sql': sql}).execute()
                
                if hasattr(result, 'error') and result.error:
                    self.stdout.write(self.style.ERROR(f'Error applying migration {migration_file}: {result.error}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Successfully applied migration: {migration_file}'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Exception applying migration {migration_file}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Migrations completed')) 