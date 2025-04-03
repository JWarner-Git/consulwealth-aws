"""
Views for financial goals functionality.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
import logging
from supabase_integration.decorators import login_required

logger = logging.getLogger(__name__)

@login_required
def goals_view(request):
    """View for managing financial goals"""
    try:
        # For now, just render a placeholder template
        context = {
            'page_title': 'Financial Goals',
        }
        
        return render(request, 'dashboard/goals.html', context)
    except Exception as e:
        logger.error(f"Error in goals view: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('dashboard:dashboard') 