from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
import jwt
from django.conf import settings
import logging
from jwt.exceptions import InvalidTokenError
from .client import get_supabase_client

User = get_user_model()
logger = logging.getLogger(__name__)

class SupabaseJWTAuthentication(BaseAuthentication):
    """
    Custom authentication class for Supabase JWT tokens
    """
    
    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        try:
            auth_parts = auth_header.split()
            if len(auth_parts) != 2 or auth_parts[0].lower() != 'bearer':
                return None
            token = auth_parts[1]
        except (ValueError, IndexError):
            return None
        
        try:
            # Decode the JWT token using the raw base64 JWT secret
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET_BASE64,  # Use the raw base64 string
                algorithms=["HS256"],
                audience="authenticated",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                }
            )
            
            # Get the user ID from the token
            user_id = payload.get('sub')
            if not user_id:
                raise AuthenticationFailed('Invalid token: No user ID')
            
            # Get the user's email from the token
            email = payload.get('email')
            if not email:
                raise AuthenticationFailed('Invalid token: No email')
            
            # Try to get the user from the database
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create a new user if they don't exist
                username = email.split('@')[0]
                # Make sure username is unique
                if User.objects.filter(username=username).exists():
                    username = f"{username}_{user_id[:8]}"
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    # Set a random password - user will need to reset it
                    password=User.objects.make_random_password()
                )
            
            # Return the user and the token payload
            return (user, payload)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidSignatureError:
            raise AuthenticationFailed('Invalid token signature')
        except jwt.DecodeError:
            raise AuthenticationFailed('Token could not be decoded')
        except InvalidTokenError as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def authenticate_header(self, request):
        return 'Bearer'


class SupabaseAuthBackend(BaseBackend):
    """
    Authentication backend that validates against Supabase Auth
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate against Supabase Auth
        """
        # Skip if no email or password
        if not email or not password:
            return None
            
        try:
            # Try to authenticate with Supabase
            client = get_supabase_client()
            
            # Attempt a Supabase Auth sign-in
            auth_response = client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if not auth_response.user:
                logger.warning(f"Supabase authentication failed for {email}")
                return None
                
            supabase_user = auth_response.user
            
            # Get or create the Django user
            try:
                user = User.objects.get(email=email)
                logger.info(f"Found existing Django user for {email}")
            except User.DoesNotExist:
                # Create a new Django user
                logger.info(f"Creating new Django user for {email}")
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=None  # We don't need to store the password in Django
                )
                user.set_unusable_password()  # Don't use Django auth
                user.save()
            
            # Since we've authenticated with Supabase, we don't need SupabaseSync
            # Just trigger the sync to ensure profile data is up to date
            logger.info(f"Signal triggered for user: {email}")
            from .services import SupabaseService
            SupabaseService.sync_user_to_supabase(user)
                
            return user
            
        except Exception as e:
            logger.error(f"Supabase authentication error for {email}: {str(e)}")
            logger.error(f"Error details: {repr(e)}")
            return None
            
    def get_user(self, user_id):
        """
        Get a user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 