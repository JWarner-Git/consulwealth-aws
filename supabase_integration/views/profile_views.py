"""
Views for user profile management.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
import logging
from supabase_integration.decorators import login_required
from supabase_integration.services import SupabaseService

logger = logging.getLogger(__name__)

@login_required
def profile_view(request):
    """User profile view"""
    try:
        # Get the user's profile data from Supabase
        supabase_id = request.user.id
        
        if not supabase_id:
            messages.error(request, "Unable to retrieve your profile. Please log in again.")
            return redirect('dashboard:dashboard')
        
        # Get profile data
        service = SupabaseService()
        profile_data = service.get_user_data(supabase_id)
        
        # Extract username from email for display
        email = request.user.email
        username = email.split('@')[0] if email else "User"
        
        # Handle form submission
        if request.method == 'POST':
            # Collect form data
            profile_updates = {
                # Personal Information
                'phone_number': request.POST.get('phone_number', ''),
                'date_of_birth': request.POST.get('date_of_birth', None),
                'address': request.POST.get('address', ''),
                
                # Financial Information
                'employment_status': request.POST.get('employment_status', ''),
                'annual_income': request.POST.get('annual_income', None),
                'net_worth': request.POST.get('net_worth', None),
                'tax_bracket': request.POST.get('tax_bracket', ''),
                
                # Investment Profile
                'risk_tolerance': request.POST.get('risk_tolerance', ''),
                'investment_experience': request.POST.get('investment_experience', ''),
                'investment_timeline': request.POST.get('investment_timeline', ''),
                'retirement_age_goal': request.POST.get('retirement_age_goal', None),
                
                # Financial Goals
                'monthly_savings_goal': request.POST.get('monthly_savings_goal', None),
                'primary_financial_goal': request.POST.get('primary_financial_goal', ''),
                'current_retirement_savings': request.POST.get('current_retirement_savings', None),
                'target_retirement_savings': request.POST.get('target_retirement_savings', None),
            }
            
            # Handle date fields - empty strings should be NULL
            if profile_updates['date_of_birth'] == '':
                profile_updates['date_of_birth'] = None
                
            # Remove empty string values for text fields that should be NULL
            for key in ['employment_status', 'risk_tolerance', 'investment_experience', 
                       'investment_timeline', 'primary_financial_goal']:
                if profile_updates[key] == '':
                    profile_updates[key] = None
            
            # Clean numeric fields
            for key in ['annual_income', 'net_worth', 'monthly_savings_goal', 
                       'current_retirement_savings', 'target_retirement_savings', 'tax_bracket']:
                if profile_updates[key] and profile_updates[key].strip():
                    try:
                        profile_updates[key] = float(profile_updates[key])
                    except ValueError:
                        profile_updates[key] = None
                else:
                    profile_updates[key] = None
            
            # Special handling for retirement_age_goal - convert to integer
            if profile_updates['retirement_age_goal'] and profile_updates['retirement_age_goal'].strip():
                try:
                    # Convert to integer by first parsing as float and then casting to int
                    profile_updates['retirement_age_goal'] = int(float(profile_updates['retirement_age_goal']))
                except ValueError:
                    profile_updates['retirement_age_goal'] = None
            else:
                profile_updates['retirement_age_goal'] = None
            
            # Convert tax_bracket to integer as well
            if profile_updates['tax_bracket'] is not None:
                profile_updates['tax_bracket'] = int(profile_updates['tax_bracket'])
                
            # Remove any keys with None values so they don't overwrite existing data
            filtered_updates = {k: v for k, v in profile_updates.items() if v is not None}
            
            # Update profile in Supabase
            try:
                updated_profile = service.update_profile(supabase_id, filtered_updates)
                messages.success(request, "Your profile has been successfully updated!")
                
                # If profile_data was None, get the newly created profile
                if profile_data is None:
                    profile_data = service.get_user_data(supabase_id)
                else:
                    # Update existing profile data with new values
                    profile_data.update(filtered_updates)
            except Exception as e:
                logger.error(f"Error updating profile: {str(e)}")
                messages.error(request, "There was an error updating your profile. Please try again.")
        
        # Calculate profile completion percentage
        profile_completion = 0
        completion_fields = [
            'phone_number', 'date_of_birth', 'address', 'employment_status', 
            'annual_income', 'net_worth', 'tax_bracket', 'risk_tolerance',
            'investment_experience', 'investment_timeline', 'retirement_age_goal',
            'monthly_savings_goal', 'primary_financial_goal'
        ]
        
        if profile_data:
            # Count number of filled fields
            filled_fields = sum(1 for field in completion_fields if profile_data.get(field))
            profile_completion = int((filled_fields / len(completion_fields)) * 100)
        
        context = {
            'page_title': 'Your Profile',
            'profile': profile_data,
            'profile_completion': profile_completion,
            'username': username
        }
        
        return render(request, 'supabase_integration/profile.html', context)
    except Exception as e:
        logger.error(f"Error retrieving profile: {str(e)}")
        messages.error(request, "An error occurred while loading your profile.")
        return redirect('dashboard:dashboard') 