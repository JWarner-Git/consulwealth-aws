from django.contrib.auth.backends import BaseBackend
import logging

logger = logging.getLogger(__name__)

class SupabaseAuthBackend(BaseBackend):
    """
    Authentication backend that uses Supabase as the source of truth.
    This backend validates credentials against Supabase and creates/updates
    shadow Django users when needed for admin functionality.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user using Supabase and create/update a shadow Django user
        """
        if not username or not password:
            return None
            
        # Determine if username is an email
        is_email = '@' in username
        email = username if is_email else None
        
        try:
            # Authenticate with Supabase
            # Import here to avoid circular imports
            from supabase_integration.services import SupabaseService
            supabase = SupabaseService()
            
            # Try to sign in with Supabase
            auth_response = supabase.client.auth.sign_in_with_password({
                'email': email or username,  # Use email if available, otherwise username
                'password': password
            })
            
            if not auth_response.user:
                logger.warning(f"Failed login attempt for {username}")
                return None
                
            # Successfully authenticated with Supabase
            supabase_user = auth_response.user
            
            # Create or update shadow Django user
            return self._get_or_create_shadow_user(supabase_user)
            
        except Exception as e:
            logger.error(f"Error authenticating with Supabase: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """
        Get a user by ID
        """
        try:
            # Import get_user_model inside the method to avoid circular imports
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def _get_or_create_shadow_user(self, supabase_user):
        """
        Creates or updates a shadow Django user based on Supabase data.
        This shadow user is only used for admin functionality and is not
        the source of truth for user data.
        """
        # Import get_user_model inside the method to avoid circular imports
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        supabase_id = supabase_user.id
        email = supabase_user.email
        
        # Try to find an existing shadow user
        try:
            # First try by supabase_id
            user = User.objects.get(supabase_id=supabase_id)
            
            # Update fields if needed
            if user.email != email:
                user.email = email
                user.save(update_fields=['email'])
                
            return user
        except User.DoesNotExist:
            # If no shadow user exists, create one
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure username is unique
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create a shadow user with unusable password
            user = User.objects.create(
                username=username,
                email=email,
                supabase_id=supabase_id
            )
            
            # Set unusable password since Supabase handles auth
            user.set_unusable_password()
            
            # Check for admin privileges in Supabase
            user.is_staff = supabase_user.user_metadata.get('is_admin', False) if supabase_user.user_metadata else False
            user.save()
            
            logger.info(f"Created shadow Django user '{username}' for Supabase user {supabase_id}")
            return user 