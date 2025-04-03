"""
Views for Supabase authentication handling.
These views replace Django's traditional authentication views.
"""
import logging
import json
import traceback
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import messages
from supabase_integration.services import SupabaseService

logger = logging.getLogger(__name__)

def login_view(request):
    """
    Handle user login through Supabase.
    This view doesn't use Django's authentication.
    """
    logger.info("Supabase login view accessed")
    
    # If user is already authenticated via Supabase token
    if request.user and request.user.is_authenticated:
        logger.info(f"User {request.user.email} already authenticated, redirecting to dashboard")
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        logger.info("Processing POST login request")
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        logger.info(f"Attempting login for email: {email}")
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'supabase_integration/login.html')
        
        # Check if environment variables are properly loaded
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.error("Supabase credentials missing in settings")
            messages.error(request, 'Server configuration error. Please contact an administrator.')
            return render(request, 'supabase_integration/login.html')
        
        # Use SupabaseService to log in
        try:
            # Initialize Supabase service
            logger.info("Initializing SupabaseService...")
            supabase = SupabaseService()
            logger.info("SupabaseService initialized successfully")
            
            # Sign in using Supabase and get the session
            logger.info("Attempting Supabase authentication...")
            auth_response = supabase.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # Extract token and store in session
            session = getattr(auth_response, 'session', None)
            user = getattr(auth_response, 'user', None)
            
            if not user:
                logger.warning(f"Authentication failed for {email} - user not found")
                messages.error(request, 'Invalid email or password. Please check your credentials.')
                return render(request, 'supabase_integration/login.html')
                
            if not session:
                logger.warning(f"Authentication succeeded for {email} but no session returned")
                messages.error(request, 'Authentication successful but session could not be created.')
                return render(request, 'supabase_integration/login.html')
            
            # Store the token in a cookie and session
            response = redirect('dashboard:dashboard')
            
            # Set secure cookie with the token
            logger.info("Setting authentication cookies and session variables")
            response.set_cookie(
                settings.SUPABASE_AUTH_TOKEN_COOKIE,
                session.access_token,
                max_age=session.expires_in,
                httponly=True,
                secure=not settings.DEBUG,  # Secure in production
                samesite='Lax'
            )
            
            # Also store in session as a backup
            request.session['supabase_token'] = session.access_token
            request.session['supabase_refresh_token'] = session.refresh_token
            
            logger.info(f"User {email} successfully logged in via Supabase")
            messages.success(request, f'Welcome back!')
            return response
            
        except Exception as e:
            logger.error(f"Supabase login error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide more specific error message based on the exception
            error_message = 'Authentication failed. Please check your credentials.'
            
            if 'Invalid login credentials' in str(e):
                error_message = 'Invalid email or password.'
            elif 'Rate limit' in str(e):
                error_message = 'Too many login attempts. Please try again later.'
            elif 'network' in str(e).lower() or 'connection' in str(e).lower():
                error_message = 'Network error. Please check your internet connection.'
            elif 'configuration' in str(e).lower() or 'key' in str(e).lower() or 'url' in str(e).lower():
                error_message = 'Server configuration error. Please contact an administrator.'
                logger.critical(f"CRITICAL CONFIGURATION ERROR: {str(e)}")
            
            messages.error(request, error_message)
    
    # GET request or failed POST
    return render(request, 'supabase_integration/login.html')

def signup_view(request):
    """
    Handle user registration through Supabase.
    This view doesn't create Django users, only Supabase users.
    """
    logger.info("Supabase signup view accessed")
    
    if request.user and request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        logger.info("Processing POST signup request")
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Basic validation
        if not email or not password:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'supabase_integration/signup.html')
            
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return render(request, 'supabase_integration/signup.html')
            
        # Use SupabaseService for registration
        supabase = SupabaseService()
        try:
            # Sign up with Supabase
            auth_response = supabase.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                logger.info(f"User {email} successfully registered via Supabase")
                messages.success(request, 'Registration successful! Please log in.')
                return redirect('supabase:login')
            else:
                logger.warning(f"Supabase signup failed for {email}")
                messages.error(request, 'Registration failed')
        except Exception as e:
            logger.exception(f"Supabase signup error: {str(e)}")
            messages.error(request, 'Registration failed: ' + str(e))
    
    # GET request or failed POST
    return render(request, 'supabase_integration/signup.html')

def logout_view(request):
    """
    Handle user logout by clearing Supabase tokens.
    This view doesn't use Django's logout functionality.
    """
    logger.info("Supabase logout view accessed")
    
    # Clear supabase tokens from session
    if 'supabase_token' in request.session:
        del request.session['supabase_token']
    if 'supabase_refresh_token' in request.session:
        del request.session['supabase_refresh_token']
    
    # Prepare response
    response = redirect(settings.LOGOUT_REDIRECT_URL)
    
    # Delete the token cookie
    response.delete_cookie(settings.SUPABASE_AUTH_TOKEN_COOKIE)
    
    messages.info(request, 'You have been successfully logged out.')
    return response

@csrf_exempt
def token_refresh(request):
    """
    API endpoint to refresh the Supabase token.
    Used by client-side JavaScript to keep the session alive.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    refresh_token = None
    
    # Get refresh token from request body
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh_token')
    except:
        pass
    
    # If not in body, try session
    if not refresh_token and 'supabase_refresh_token' in request.session:
        refresh_token = request.session.get('supabase_refresh_token')
    
    if not refresh_token:
        return JsonResponse({'error': 'No refresh token provided'}, status=400)
    
    try:
        # Use the refresh token to get a new access token
        supabase = SupabaseService()
        auth_response = supabase.client.auth.refresh_session(refresh_token)
        
        if auth_response.session:
            # Update the tokens in session
            request.session['supabase_token'] = auth_response.session.access_token
            request.session['supabase_refresh_token'] = auth_response.session.refresh_token
            
            # Return the new tokens
            return JsonResponse({
                'access_token': auth_response.session.access_token,
                'refresh_token': auth_response.session.refresh_token,
                'expires_in': auth_response.session.expires_in
            })
        else:
            logger.warning("Token refresh failed - no session returned")
            return JsonResponse({'error': 'Token refresh failed'}, status=401)
    except Exception as e:
        logger.exception(f"Token refresh error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=401) 