from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from supabase_integration.client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

@login_required
def subscription_view(request):
    """
    View for the subscription page where users can subscribe to premium plans.
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
        'active_page': 'subscription',
        'page_title': 'Subscription Management',
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
        **subscription_data
    }
    
    return render(request, 'dashboard/subscription.html', context) 