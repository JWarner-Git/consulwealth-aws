"""
Management command to import account data from transactions.
This command reads a transactions CSV file and creates accounts for any unique account_ids found,
associating them with the specified user.
"""
import csv
import logging
from django.core.management.base import BaseCommand
from supabase_integration.adapter import SupabaseAdapter
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import account data from transactions CSV file'

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=str, required=True, help='The Supabase user ID to associate accounts with')
        parser.add_argument('--csv_file', type=str, required=True, help='Path to the transactions CSV file')
        parser.add_argument('--dry_run', action='store_true', help='Show what would be done without making changes')

    def handle(self, *args, **options):
        user_id = options['user_id']
        csv_file = options['csv_file']
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(f"Importing account data for user {user_id} from {csv_file}")
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        # Initialize Supabase adapter
        adapter = SupabaseAdapter()
        
        try:
            # First, get existing accounts for the user
            existing_accounts = adapter.get_accounts(user_id)
            existing_account_ids = [account['account_id'] for account in existing_accounts if 'account_id' in account]
            
            self.stdout.write(f"Found {len(existing_accounts)} existing accounts for user")
            
            # Now read the transactions CSV and find all unique account_ids
            transaction_account_ids = set()
            
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if 'account_id' in row and row['account_id']:
                        transaction_account_ids.add(row['account_id'])
            
            self.stdout.write(f"Found {len(transaction_account_ids)} unique account IDs in transactions")
            
            # Identify account IDs that need to be created
            new_account_ids = [acc_id for acc_id in transaction_account_ids if acc_id not in existing_account_ids]
            
            self.stdout.write(f"Need to create {len(new_account_ids)} new accounts")
            
            # Create accounts for each missing account ID
            created_accounts = 0
            for account_id in new_account_ids:
                # Create a basic account record with the essential fields
                account_data = {
                    'account_id': account_id,
                    'name': f"Account {account_id[-6:]}",  # Use last 6 chars of UUID as identifier
                    'type': 'depository',  # Default type
                    'subtype': 'checking',  # Default subtype
                    'current_balance': 0.0,
                    'available_balance': 0.0,
                }
                
                self.stdout.write(f"{'Would create' if dry_run else 'Creating'} account: {account_data['name']}")
                
                if not dry_run:
                    # Store the account with the user ID
                    result = adapter.store_account(user_id, account_data)
                    
                    if result:
                        created_accounts += 1
                        self.stdout.write(self.style.SUCCESS(f"Created account: {account_data['name']}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to create account: {account_data['name']}"))
            
            # Summary
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would create {len(new_account_ids)} accounts"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Successfully created {created_accounts} accounts"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error importing account data: {str(e)}"))
            logger.exception("Error in import_account_data command") 