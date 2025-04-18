"""
Views for user profile management.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
import logging
from supabase_integration.decorators import login_required
from supabase_integration.services import SupabaseService
from django.views.decorators.http import require_POST
from supabase_integration.client import get_supabase_client
from django.conf import settings

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

@login_required
@require_POST
def delete_account(request):
    """Handle account deletion."""
    try:
        supabase_id = request.user.id
        user_email = request.user.email
        
        if not supabase_id:
            messages.error(request, "Unable to identify your account. Please log in again.")
            return redirect('profile')
        
        logger.info(f"Processing account deletion for user {supabase_id}")
        
        # Step 1: Cancel any active subscriptions
        try:
            from subscriptions.services import StripeService
            stripe_service = StripeService()
            cancellation_result = stripe_service.cancel_subscription(request.user)
            
            if cancellation_result.get('success', False):
                logger.info(f"Successfully cancelled subscription for user {supabase_id}")
            else:
                logger.warning(f"No active subscription found or cancellation failed for user {supabase_id}")
        except Exception as sub_error:
            logger.error(f"Error cancelling subscription: {str(sub_error)}")
        
        # Step 2: Delete user data from Supabase
        try:
            client = get_supabase_client()
            
            # Delete from profiles table
            profile_response = client.table('profiles').delete().eq('id', supabase_id).execute()
            logger.info(f"Profile deletion response: {profile_response}")
            
            # Delete from auth.users using admin APIs if enabled
            if hasattr(settings, 'SUPABASE_SECRET') and settings.SUPABASE_SECRET:
                try:
                    import requests
                    
                    # This requires Supabase Service Role Key for auth admin access
                    admin_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{supabase_id}"
                    headers = {
                        'apikey': settings.SUPABASE_KEY,
                        'Authorization': f'Bearer {settings.SUPABASE_SECRET}'
                    }
                    
                    response = requests.delete(admin_url, headers=headers)
                    logger.info(f"Auth user deletion response: {response.status_code}")
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully deleted auth user {supabase_id}")
                    else:
                        logger.warning(f"Failed to delete auth user from Supabase: {response.text}")
                except Exception as auth_error:
                    logger.error(f"Error deleting auth user: {str(auth_error)}")
        except Exception as db_error:
            logger.error(f"Error deleting user data from Supabase: {str(db_error)}")
            messages.error(request, "There was an error deleting your account data.")
            return redirect('profile')
        
        # Step 3: Delete Django shadow user if it exists
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Try to find user by email or Supabase ID
            django_users = User.objects.filter(email=user_email)
            if django_users.exists():
                for user in django_users:
                    user.delete()
                    logger.info(f"Deleted Django shadow user with email {user_email}")
        except Exception as django_error:
            logger.error(f"Error deleting Django shadow user: {str(django_error)}")
        
        # Step 4: Clear session and redirect
        messages.success(request, "Your account has been successfully deleted.")
        
        # Clear the session
        request.session.flush()
        
        # Redirect to login page
        return redirect('supabase:login')
        
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        messages.error(request, "An error occurred while deleting your account. Please try again or contact support.")
        return redirect('profile') 