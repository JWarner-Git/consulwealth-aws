"""
Views for support functionality.
"""
from django.shortcuts import render
import logging
from supabase_integration.decorators import login_required

logger = logging.getLogger(__name__)

@login_required
def support_view(request):
    """Support view"""
    context = {
        'page_title': 'Support Center',
    }
    
    return render(request, 'dashboard/support.html', context) 