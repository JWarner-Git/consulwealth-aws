from django.shortcuts import render, redirect
import stripe
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Subscription
from datetime import datetime, timedelta
from supabase_integration.adapter import SupabaseAdapter
from supabase_integration.client import get_supabase_client
import uuid
from django.contrib.auth import get_user_model
from .services import StripeService
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe API
stripe.api_key = settings.STRIPE_SECRET_KEY

# Initialize Stripe service
stripe_service = StripeService()

# Direct Supabase update function that bypasses the adapter using direct API calls
def update_supabase_profile_directly(user_id, profile_data):
    """
    Update a Supabase profile directly using multiple approaches
    """
    try:
        # Get Supabase client
        client = get_supabase_client()
        
        # Print debug info
        print(f"Direct API update for user ID: {user_id}")
        print(f"Data to update: {profile_data}")
        
        # Try multiple approaches one by one until one works
        
        # Approach 1: Simple JSON update with explicit ID matching
        try:
            print("Trying approach 1: Simple update")
            # Add the ID to the data payload
            update_data = profile_data.copy()
            
            # Execute update
            response = client.table('profiles').update(update_data).eq('id', user_id).execute()
            print(f"Approach 1 response: {response}")
            if response.data:
                return True
        except Exception as e1:
            print(f"Approach 1 failed: {str(e1)}")
        
        # Approach 2: Try using REST API directly
        try:
            print("Trying approach 2: REST API")
            import requests
            from django.conf import settings
            
            # Prepare the request
            url = f"{settings.SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}"
            headers = {
                'apikey': settings.SUPABASE_KEY,
                'Authorization': f'Bearer {settings.SUPABASE_SECRET}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            # Create safe data format with no nested objects - convert all values to strings
            safe_data = {}
            for key, value in profile_data.items():
                if isinstance(value, bool):
                    safe_data[key] = value  # Booleans should be sent as-is
                elif value is not None:
                    safe_data[key] = str(value)  # Convert everything else to strings
            
            print(f"Sending safe data: {safe_data}")
            
            # Send the PATCH request
            response = requests.patch(url, json=safe_data, headers=headers)
            print(f"Approach 2 response: {response.status_code} - {response.text}")
            if response.status_code in (200, 201, 204):
                return True
                
            # Try alternative URL format if that didn't work
            alt_url = f"{settings.SUPABASE_URL}/rest/v1/profiles?id=eq.\"{user_id}\""
            print(f"Trying alternative URL: {alt_url}")
            alt_response = requests.patch(alt_url, json=safe_data, headers=headers)
            print(f"Alternative response: {alt_response.status_code} - {alt_response.text}")
            if alt_response.status_code in (200, 201, 204):
                return True
        except Exception as e2:
            print(f"Approach 2 failed: {str(e2)}")
        
        # Approach 3: Single field updates
        try:
            print("Trying approach 3: Single field updates")
            # Update each field individually
            for key, value in profile_data.items():
                field_data = {key: value}
                try:
                    field_response = client.table('profiles').update(field_data).eq('id', user_id).execute()
                    print(f"Field update for {key}: {field_response}")
                except Exception as field_error:
                    print(f"Error updating field {key}: {str(field_error)}")
            
            return True
        except Exception as e3:
            print(f"Approach 3 failed: {str(e3)}")
        
        # If all approaches failed
        return False
            
    except Exception as e:
        print(f"Error in direct updates: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@login_required
@require_POST
@csrf_exempt
def create_subscription(request):
    """
    Create a new Stripe subscription for the user
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        token = data.get('stripeToken')
        plan = data.get('plan', 'premium')  # Default to premium plan
        
        # Use our new StripeService to handle the subscription creation
        result = stripe_service.create_subscription(request.user, token, plan)
        
        if result:
            return JsonResponse({
                'success': True,
                'subscription': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create subscription'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def subscription_status(request):
    """
    Get the subscription status for the current user
    """
    try:
        # Get subscription status from StripeService
        status = stripe_service.get_subscription_status(request.user)
        
        return render(request, 'subscriptions/status.html', {
            'page_title': 'Subscription Status',
            'subscription': status
        })
    
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        return render(request, 'subscriptions/status.html', {
            'page_title': 'Subscription Status',
            'error': str(e)
        })

@login_required
@require_POST
def cancel_subscription(request):
    """
    Cancel the user's subscription
    """
    try:
        # Cancel subscription using StripeService
        result = stripe_service.cancel_subscription(request.user)
        
        # Update the Supabase user profile directly
        if result.get('success', False):
            user_id = request.user.id
            
            profile_data = {
                'subscription_status': 'cancelled',
            }
            
            # Try to update the profile directly
            update_result = update_supabase_profile_directly(user_id, profile_data)
            
            if not update_result:
                logger.error(f"Failed to update Supabase profile for user {user_id}")
        
        # Check if it's an AJAX request
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse(result)
        else:
            # If it's a regular form submission, redirect to the subscription page with a success message
            return redirect('subscriptions:subscription_page')
    
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        
        # Check if it's an AJAX request
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        else:
            # If it's a regular form submission, redirect to the subscription page with an error message
            return redirect('subscriptions:subscription_page')

@login_required
def debug_user_id(request):
    """Debug endpoint to see the current user ID"""
    return JsonResponse({
        'user_id': str(request.user.id),
        'user_email': request.user.email
    })

@login_required
def update_profile_to_premium(request):
    """Manually update a user's profile to premium status"""
    try:
        # Update the profile using StripeService
        success = stripe_service.update_profile_to_premium(request.user)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Profile updated to premium status'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to update profile'
            })
    
    except Exception as e:
        logger.error(f"Error updating profile to premium: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# Add this new view for standalone subscription page
@login_required
def subscription_page(request):
    """
    Standalone subscription page that's not under the dashboard namespace.
    This is accessible to non-subscribers.
    """
    user_id = request.user.id
    subscription_data = {}
    
    try:
        # Get Supabase client and fetch the user's profile
        client = get_supabase_client()
        response = client.table('profiles').select('*').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            user_profile = response.data[0]
            
            # Check if the user is a premium subscriber
            is_premium_subscriber = user_profile.get('is_premium_subscriber', False)
            subscription_plan = user_profile.get('subscription_plan', '')
            subscription_status = user_profile.get('subscription_status', '')
            subscription_end_date = user_profile.get('subscription_end_date', None)
            
            subscription_data = {
                'is_premium_subscriber': is_premium_subscriber,
                'subscription_plan': subscription_plan,
                'subscription_status': subscription_status,
                'subscription_end_date': subscription_end_date
            }
        
    except Exception as e:
        logger.error(f"Error fetching subscription data: {str(e)}")
        subscription_data = {
            'is_premium_subscriber': False
        }
    
    context = {
        'page_title': 'Choose Your Plan',
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
        **subscription_data
    }
    
    return render(request, 'subscriptions/subscription_page.html', context)
