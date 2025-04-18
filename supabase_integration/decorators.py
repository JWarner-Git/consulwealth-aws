"""
Authentication decorators for Supabase integration.
These decorators replace Django's built-in authentication decorators.
"""
import logging
import functools
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth import login
from django.conf import settings
import jwt
from supabase_integration.adapter import SupabaseAdapter

logger = logging.getLogger(__name__)

def login_required(view_func=None, login_url=None, forbidden_message=None):
    """
    Decorator for views that checks that the user is logged in via Supabase,
    redirecting to the log-in page if necessary.
    
    Args:
        view_func: The view function to decorate
        login_url: The URL to redirect to if the user is not authenticated
        forbidden_message: Custom message for forbidden responses
        
    Returns:
        The decorated view function
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            else:
                # Determine login URL - use the one passed to the decorator or get from settings
                redirect_url = login_url
                if not redirect_url:
                    # Try to get login URL from settings or default to /auth/login/
                    try:
                        from django.conf import settings
                        redirect_url = settings.LOGIN_URL
                    except (ImportError, AttributeError):
                        redirect_url = '/auth/login/'
                    
                return redirect(redirect_url)
        return _wrapped_view
    
    if view_func:
        return decorator(view_func)
    return decorator

def admin_required(view_func=None, login_url=None):
    """
    Decorator for views that checks that the user is an admin,
    redirecting to the log-in page if necessary.
    
    Args:
        view_func: The view function to decorate
        login_url: The URL to redirect to if the user is not authenticated
        
    Returns:
        The decorated view function
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('/auth/login/')
                
            # Check if user is admin (from Supabase profile)
            is_admin = request.user.raw_data.get('is_admin', False)
            if not is_admin:
                return HttpResponseForbidden("Admin access required")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    
    if view_func:
        return decorator(view_func)
    return decorator

def role_required(role):
    """
    Decorator for views that checks if the user has a specific role.
    
    Args:
        role: The required role (string)
        
    Returns:
        A decorator function
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/auth/login/')
                
            # Check user roles from Supabase profile
            user_roles = request.user.raw_data.get('roles', [])
            if isinstance(user_roles, str):
                user_roles = [user_roles]
                
            if role not in user_roles:
                return HttpResponseForbidden(f"Role '{role}' required")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def jwt_auth_required(view_func):
    """
    Authentication decorator for mobile API endpoints.
    Validates JWT token from Authorization header and sets request.user.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get the Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        # Check if the header starts with 'Bearer '
        if not auth_header.startswith('Bearer '):
            logger.error('Missing or invalid Authorization header')
            return JsonResponse({
                'success': False,
                'error': 'Missing or invalid Authorization header'
            }, status=401)
        
        # Extract the token
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        try:
            # Initialize Supabase adapter
            adapter = SupabaseAdapter()
            
            # Verify the JWT token
            # This can be done either by:
            # 1. Using the Supabase JWT verification if available
            # 2. Decoding and verifying the JWT manually with the jwt library
            try:
                # Option 1: Use Supabase's verification (preferred)
                user = adapter.verify_jwt_token(token)
                request.user = user
            except (AttributeError, NotImplementedError):
                # Option 2: Manual verification
                # Note: For production, you should get the JWT secret from a secure configuration
                decoded = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    options={"verify_signature": True}
                )
                
                # Get the user ID from the decoded token
                user_id = decoded.get('sub')
                if not user_id:
                    raise ValueError('Invalid token: missing user ID')
                
                # Get the user from Supabase
                user = adapter.get_user_by_id(user_id)
                if not user:
                    raise ValueError('User not found')
                
                request.user = user
                
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f'JWT authentication error: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': 'Authentication failed'
            }, status=401)
    
    return wrapper 