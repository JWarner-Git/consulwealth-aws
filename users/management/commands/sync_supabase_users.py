from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import logging

from supabase_integration.services import SupabaseService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronizes Supabase users to Django shadow users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update of all users even if they already exist',
        )
        parser.add_argument(
            '--clean-orphans',
            action='store_true',
            help='Mark shadow Django users as inactive if they no longer exist in Supabase',
        )

    def handle(self, *args, **options):
        force_update = options.get('force_update', False)
        clean_orphans = options.get('clean_orphans', False)
        User = get_user_model()
        
        self.stdout.write('Starting Supabase user synchronization...')
        
        try:
            # Initialize the Supabase service
            supabase_service = SupabaseService()
            
            # Synchronize all users from Supabase to Django
            sync_count = supabase_service.sync_all_users()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully synchronized {sync_count} users from Supabase to Django'))
            
            # Handle orphaned users if requested
            if clean_orphans:
                self.stdout.write('Checking for orphaned Django users...')
                
                # Get all Supabase user IDs
                response = supabase_service.client.auth.admin.list_users()
                supabase_users = response.users if response else []
                supabase_ids = [user.id for user in supabase_users]
                
                # Find Django users with Supabase IDs that no longer exist in Supabase
                orphaned_users = User.objects.filter(supabase_id__isnull=False).exclude(supabase_id__in=supabase_ids)
                orphan_count = orphaned_users.count()
                
                if orphan_count > 0:
                    # Mark orphaned users as inactive
                    orphaned_users.update(is_active=False)
                    self.stdout.write(self.style.WARNING(f'Marked {orphan_count} orphaned Django users as inactive'))
                else:
                    self.stdout.write('No orphaned Django users found')
            
            return sync_count
            
        except Exception as e:
            logger.error(f"Error synchronizing Supabase users: {str(e)}")
            raise CommandError(f'Failed to synchronize Supabase users: {str(e)}') 