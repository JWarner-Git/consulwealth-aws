from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

@login_required
def subscription_view(request):
    """
    View for the subscription page where users can subscribe to premium plans.
    """
    return render(request, 'dashboard/subscription.html', {
        'active_page': 'subscription',
        'page_title': 'Choose Your Plan',
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
    }) 