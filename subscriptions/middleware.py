"""
Middleware for subscription access control.
This middleware checks if a user has an active subscription and redirects
non-subscribers to the welcome page for certain protected routes.
"""
import logging
import re
from django.shortcuts import redirect
from django.urls import reverse

from .services import StripeService

logger = logging.getLogger(__name__)

class SubscriptionRequiredMiddleware:
    """
    Middleware that checks if a user has an active subscription.
    If not, they are redirected to the welcome page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.stripe_service = StripeService()
        
        # Define protected paths that require a subscription
        self.protected_paths = [
            r'^/dashboard/',  # Dashboard and all subpaths
            r'^/profile/',    # User profile
        ]
        
        # Define allowed paths that don't require a subscription
        self.allowed_paths = [
            r'^/welcome/',    # Welcome page
            r'^/auth/',       # Authentication pages
            r'^/subscriptions/', # Subscription management
            r'^/dashboard/subscription/', # Subscription page (allow access even though it's under dashboard)
            r'^/admin/',      # Admin pages
            r'^/static/',     # Static files
            r'^/media/',      # Media files
            r'^/api/',        # API endpoints
            r'^/favicon.ico$', # Favicon
        ]
        
        # Required attribute for Django's middleware
        self.async_mode = False
        
        logger.info("Subscription middleware initialized")
    
    def __call__(self, request):
        """
        Process each request to check subscription status.
        
        Redirects non-subscribers to the welcome page if they try to access
        protected paths.
        """
        current_path = request.path
        
        # Skip checks for unauthenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return self.get_response(request)
        
        # Check if the current path is in the allowed list
        for pattern in self.allowed_paths:
            if re.match(pattern, current_path):
                return self.get_response(request)
        
        # Only check for subscription if trying to access a protected path
        is_protected = False
        for pattern in self.protected_paths:
            if re.match(pattern, current_path):
                is_protected = True
                break
        
        # If not a protected path, allow access
        if not is_protected:
            return self.get_response(request)
            
        # Check if user has an active subscription
        try:
            user = request.user
            logger.debug(f"Checking subscription for user {user.id}")
            
            # Get subscription status
            subscription_status = self.stripe_service.get_subscription_status(user)
            logger.debug(f"Subscription status: {subscription_status}")
            
            # Check if user has an active subscription
            if (subscription_status.get('success') and 
                subscription_status.get('has_subscription') and 
                subscription_status.get('is_active')):
                # User has an active subscription, allow access
                return self.get_response(request)
            
            # No active subscription, redirect to welcome page
            logger.info(f"User {user.id} does not have an active subscription, redirecting to welcome page")
            
            # Redirect to welcome page
            return redirect('welcome')
        
        except Exception as e:
            # Log the error but still allow access (fail open)
            logger.error(f"Error checking subscription status: {str(e)}")
            
            # In case of error, we allow access rather than blocking users
            return self.get_response(request) 