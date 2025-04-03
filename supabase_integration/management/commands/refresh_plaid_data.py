"""
Management command to refresh Plaid data periodically.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from supabase_integration.services import PlaidService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Refreshes Plaid data for all users based on refresh schedule'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='soft',
            help='Type of refresh to perform (soft or hard)'
        )
        parser.add_argument(
            '--user_id',
            type=str,
            help='Specific user ID to refresh (optional)'
        )
    
    def handle(self, *args, **options):
        refresh_type = options.get('type')
        user_id = options.get('user_id')
        
        plaid_service = PlaidService()
        
        try:
            if user_id:
                # Refresh a specific user
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                    self.refresh_user_data(plaid_service, user, refresh_type)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
            else:
                # Refresh all users based on schedule
                self.refresh_scheduled_items(plaid_service, refresh_type)
        except Exception as e:
            logger.error(f"Error refreshing Plaid data: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error refreshing Plaid data: {str(e)}"))
    
    def refresh_user_data(self, plaid_service, user, refresh_type):
        """Refresh data for a specific user"""
        if refresh_type == 'soft':
            # For soft refresh, update accounts and transactions
            self.stdout.write(f"Performing soft refresh for user {user.id}")
            
            try:
                # Update accounts
                accounts = plaid_service.refresh_accounts(user)
                self.stdout.write(f"Updated {len(accounts)} accounts for user {user.id}")
                
                # Update transactions for the last 30 days
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                transactions = plaid_service.refresh_transactions(user, start_date, end_date)
                self.stdout.write(f"Updated {len(transactions)} transactions for user {user.id}")
                
                # Get the user's Plaid items and record the refresh
                plaid_items = plaid_service.adapter.get_plaid_items(str(user.id))
                for item in plaid_items:
                    plaid_service.adapter.record_soft_refresh(item['id'])
                
                self.stdout.write(self.style.SUCCESS(f"Successfully refreshed data for user {user.id}"))
            except Exception as e:
                logger.error(f"Error performing soft refresh for user {user.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error performing soft refresh for user {user.id}: {str(e)}"))
        else:
            # For hard refresh, we can't do this automatically
            # as it requires user interaction with Plaid Link
            self.stdout.write(self.style.WARNING(
                f"Hard refresh requires user interaction and cannot be done through a command."
            ))
    
    def refresh_scheduled_items(self, plaid_service, refresh_type):
        """Refresh items based on schedule"""
        User = get_user_model()
        
        # Get items needing refresh
        try:
            items_to_refresh = plaid_service.adapter.get_items_needing_refresh(
                refresh_type=refresh_type
            )
            
            self.stdout.write(f"Found {len(items_to_refresh)} items needing {refresh_type} refresh")
            
            if refresh_type == 'soft':
                # Process soft refreshes
                for item in items_to_refresh:
                    try:
                        # Get the user for this item
                        user_id = item.get('user_id')
                        try:
                            user = User.objects.get(supabase_id=user_id)
                            
                            # Refresh accounts and transactions
                            plaid_service.refresh_accounts(user)
                            
                            # Update transactions for the last 30 days
                            end_date = datetime.now().date()
                            start_date = end_date - timedelta(days=30)
                            plaid_service.refresh_transactions(user, start_date, end_date)
                            
                            # Record the refresh
                            plaid_service.adapter.record_soft_refresh(item['id'])
                            
                            self.stdout.write(self.style.SUCCESS(
                                f"Successfully refreshed item {item['id']} for user {user_id}"
                            ))
                        except User.DoesNotExist:
                            logger.warning(f"User with Supabase ID {user_id} not found")
                            self.stdout.write(self.style.WARNING(
                                f"User with Supabase ID {user_id} not found"
                            ))
                    except Exception as e:
                        logger.error(f"Error refreshing item {item['id']}: {str(e)}")
                        self.stdout.write(self.style.ERROR(
                            f"Error refreshing item {item['id']}: {str(e)}"
                        ))
            else:
                # For hard refreshes, we can't do this automatically
                # We'll log which items need a hard refresh so a notification system
                # could be used to prompt users to reconnect
                for item in items_to_refresh:
                    user_id = item.get('user_id')
                    self.stdout.write(self.style.WARNING(
                        f"Item {item['id']} for user {user_id} needs a hard refresh "
                        f"(last connected: {item.get('last_connection_time', 'unknown')})"
                    ))
                
                self.stdout.write(self.style.WARNING(
                    f"Hard refreshes require user interaction and will need to be "
                    f"prompted through the UI or notification system."
                ))
                
        except Exception as e:
            logger.error(f"Error getting items needing refresh: {str(e)}")
            self.stdout.write(self.style.ERROR(
                f"Error getting items needing refresh: {str(e)}"
            )) 