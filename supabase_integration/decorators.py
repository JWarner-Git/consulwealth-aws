"""
Authentication decorators for Supabase integration.
These decorators replace Django's built-in authentication decorators.
"""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

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
        @wraps(view_func)
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
        @wraps(view_func)
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
        @wraps(view_func)
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