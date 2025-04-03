"""
Middleware for Supabase authentication integration with Django.
This module provides middleware classes that handle Supabase auth tokens and session management.
"""
import logging
import json
import time
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from .services import SupabaseService

logger = logging.getLogger(__name__)

class SupabaseUser:
    """
    User class that replaces Django's User model for authentication.
    This represents a user authenticated via Supabase.
    """
    
    def __init__(self, user_data=None):
        # Ensure user_data is treated as a dictionary, even if it's an object with attributes
        if user_data and not isinstance(user_data, dict):
            # Convert Supabase user object to dictionary if needed
            self.is_authenticated = True
            self.id = getattr(user_data, 'id', None)
            self.email = getattr(user_data, 'email', None)
            # Create a raw_data dictionary from user_data attributes
            self.raw_data = {
                'id': self.id,
                'email': self.email,
                'user_metadata': getattr(user_data, 'user_metadata', {}),
                'app_metadata': getattr(user_data, 'app_metadata', {})
            }
        else:
            # Normal dictionary handling
            self.is_authenticated = bool(user_data)
            self.id = user_data.get('id') if user_data else None
            self.email = user_data.get('email') if user_data else None
            self.raw_data = user_data or {}
        
        # Map common Django User model attributes
        self.username = self.email
        self.first_name = self.raw_data.get('user_metadata', {}).get('first_name', '') if isinstance(self.raw_data.get('user_metadata'), dict) else ''
        self.last_name = self.raw_data.get('user_metadata', {}).get('last_name', '') if isinstance(self.raw_data.get('user_metadata'), dict) else ''
        self.is_staff = self.raw_data.get('is_staff', False)
        self.is_superuser = self.raw_data.get('is_superuser', False)
        
    def __str__(self):
        return self.email or "Anonymous User"
        
    def get_role(self):
        """Get the user's role from Supabase data"""
        return self.raw_data.get('role', None)
        
    def is_admin(self):
        """Check if the user has admin privileges"""
        return self.raw_data.get('is_admin', False)
        
    @property
    def is_anonymous(self):
        """Opposite of is_authenticated, included for compatibility with Django templates"""
        return not self.is_authenticated


class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware that processes Supabase authentication tokens.
    This middleware is responsible for:
    1. Extracting Supabase tokens from headers, cookies, or session
    2. Validating tokens and retrieving user information
    3. Setting up the request.user object
    
    It replaces Django's auth middleware and doesn't use Django's User model.
    """
    
    def process_request(self, request):
        """Process each request to validate Supabase authentication"""
        # Always check for a Supabase token first
        token = self._get_token_from_request(request)
        
        if not token:
            logger.debug("No Supabase token found in request")
            # For non-admin URLs, set an anonymous Supabase user
            if not request.path.startswith('/admin/'):
                request.user = SupabaseUser()
            return None
            
        # Validate token and get user data from Supabase
        try:
            # Initialize Supabase service
            supabase = SupabaseService()
            
            # Decode the token to check if it's still valid
            user_data = supabase.client.auth.get_user(token).user
            
            if user_data:
                # Set authenticated Supabase user
                supabase_user = SupabaseUser(user_data)
                
                # For admin URLs, we need to sync with a Django User
                if request.path.startswith('/admin/'):
                    # Create or update a shadow Django user
                    django_user = self._get_or_create_shadow_user(supabase_user)
                    # Django's middleware will use this user
                else:
                    # For non-admin URLs, we use the Supabase user directly
                    request.user = supabase_user
                    
                logger.debug(f"Authenticated Supabase user: {supabase_user.email}")
            else:
                logger.warning("Invalid or expired Supabase token")
                # Clear invalid token
                self._clear_token(request)
                # For non-admin URLs, set anonymous user
                if not request.path.startswith('/admin/'):
                    request.user = SupabaseUser()
        except Exception as e:
            logger.warning(f"Error validating Supabase token: {str(e)}")
            # Clear invalid token
            self._clear_token(request)
            # For non-admin URLs, set anonymous user
            if not request.path.startswith('/admin/'):
                request.user = SupabaseUser()
            
        return None
    
    def _get_token_from_request(self, request):
        """
        Extract Supabase token from various sources in the request.
        Priority order: Authorization header > Cookie > Session
        """
        # 1. Check Authorization header (for API requests)
        auth_header = request.META.get(settings.SUPABASE_AUTH_HEADER, '')
        if auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
            
        # 2. Check for token in cookies
        token_cookie = settings.SUPABASE_AUTH_TOKEN_COOKIE
        if token_cookie in request.COOKIES:
            return request.COOKIES.get(token_cookie)
            
        # 3. Check session
        if 'supabase_token' in request.session:
            return request.session.get('supabase_token')
            
        return None
    
    def _clear_token(self, request):
        """Clear invalid token from session and prepare to clear from cookies"""
        if 'supabase_token' in request.session:
            del request.session['supabase_token']
        if 'supabase_refresh_token' in request.session:
            del request.session['supabase_refresh_token']
            
        # Note: We can't clear cookies directly here because middleware doesn't 
        # have access to the response. The view will need to clear the cookie
        # when it detects an authentication failure. 
    
    def _get_or_create_shadow_user(self, supabase_user):
        """
        Get or create a shadow Django user based on Supabase user.
        This creates minimally-populated Django User objects that
        reference the corresponding Supabase user.
        
        The Django user is NEVER the source of truth - it's just a shadow
        that enables admin functionality.
        """
        # Import here to avoid circular imports
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            # First try to find by supabase_id
            user = User.objects.get(supabase_id=supabase_user.id)
            
            # Ensure shadow user is in sync with Supabase
            if user.email != supabase_user.email:
                user.email = supabase_user.email
                user.save(update_fields=['email'])
                
            return user
        except User.DoesNotExist:
            # Create a new shadow user
            username = supabase_user.email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure username is unique
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
                
            # Create a shadow user with an unusable password (can't log in directly)
            user = User.objects.create(
                username=username,
                email=supabase_user.email,
                supabase_id=supabase_user.id
            )
            user.set_unusable_password()
            
            # Set is_staff based on Supabase admin status
            user.is_staff = supabase_user.raw_data.get('is_admin', False)
            user.save()
            
            logger.info(f"Created shadow Django user for Supabase user: {supabase_user.id}")
            return user 