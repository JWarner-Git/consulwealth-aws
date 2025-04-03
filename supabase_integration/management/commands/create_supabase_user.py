"""
Management command to create a Supabase-only user.
This command allows you to create a user in Supabase directly from the command line,
without creating a Django User model (unless explicitly requested).
"""
import logging
from django.core.management.base import BaseCommand
from supabase_integration.services import SupabaseService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a new user in Supabase without creating a Django User model'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address for the new user')
        parser.add_argument('password', type=str, help='Password for the new user')
        parser.add_argument('--admin', action='store_true', 
                            help='Make this user an admin in Supabase')
        parser.add_argument('--first-name', type=str, 
                            help='First name for the user profile')
        parser.add_argument('--last-name', type=str, 
                            help='Last name for the user profile')
        parser.add_argument('--create-django-user', action='store_true',
                            help='Also create a corresponding Django user (for admin access)')
        parser.add_argument('--django-superuser', action='store_true',
                            help='Make the Django user a superuser (requires --create-django-user)')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        is_admin = options['admin']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')
        create_django_user = options['create_django_user']
        django_superuser = options['django_superuser']
        
        self.stdout.write(f"Creating Supabase user with email: {email}")
        
        try:
            # Use the SupabaseService to create the user
            supabase = SupabaseService()
            
            # Sign up with Supabase Auth
            response = supabase.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_admin": is_admin
                    }
                }
            })
            
            if response.user:
                supabase_user_id = response.user.id
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully created Supabase user with ID: {supabase_user_id}"
                ))
                
                # Now create or update the profile
                from supabase_integration.adapter import UserAdapter
                adapter = UserAdapter()
                
                # Prepare profile data
                profile_data = {
                    'id': supabase_user_id,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_admin': is_admin
                }
                
                success = adapter.update_profile(supabase_user_id, profile_data)
                
                if success:
                    self.stdout.write(self.style.SUCCESS("Profile created/updated successfully"))
                else:
                    self.stdout.write(self.style.WARNING(
                        "User created but there was an issue updating the profile. "
                        "You may need to complete the profile manually."
                    ))
                
                # Optionally create a Django user for admin access
                if create_django_user:
                    self.stdout.write("Creating corresponding Django user...")
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    # Derive a username from the email if needed
                    username = email.split('@')[0]
                    base_username = username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}_{counter}"
                        counter += 1
                    
                    # Create the user
                    if django_superuser:
                        user = User.objects.create_superuser(
                            username=username,
                            email=email,
                            password=password
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"Created Django superuser '{username}' for admin access"
                        ))
                    else:
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"Created Django user '{username}'"
                        ))
                    
                    # Link the Django user to the Supabase ID
                    user.supabase_id = supabase_user_id
                    user.save()
                
                return
            else:
                self.stdout.write(self.style.ERROR("Failed to create Supabase user"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating Supabase user: {str(e)}")) 