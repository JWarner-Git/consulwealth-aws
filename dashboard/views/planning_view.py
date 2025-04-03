"""
Views for retirement planning functionality.
"""
from django.shortcuts import render
from django.http import JsonResponse
import json
import logging
from supabase_integration.decorators import login_required
from supabase_integration.services import SupabaseService
from supabase_integration.adapter import SupabaseAdapter

logger = logging.getLogger(__name__)

@login_required
def planning_view(request):
    """Retirement planning view"""
    try:
        # Get user's email
        user_email = request.user.email
        
        # Connect to Supabase to fetch user profile
        adapter = SupabaseAdapter()
        
        # Try to find the user profile
        user_profile = None
        try:
            # Query profiles table by email
            profiles = adapter.client.table('profiles').select('*').eq('email', user_email).execute()
            if profiles.data and len(profiles.data) > 0:
                user_profile = profiles.data[0]
                
                # Calculate current age if date of birth exists
                if user_profile.get('date_of_birth'):
                    from datetime import datetime
                    try:
                        dob = datetime.strptime(user_profile['date_of_birth'], '%Y-%m-%d').date()
                        today = datetime.now().date()
                        user_profile['current_age'] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    except Exception as e:
                        logger.error(f"Error calculating age: {str(e)}")
                        user_profile['current_age'] = 30
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            
        context = {
            'page_title': 'Retirement Planning',
            'user_profile': user_profile or {},
        }
        
        return render(request, 'dashboard/planning.html', context)
    except Exception as e:
        logger.error(f"Error in planning view: {str(e)}")
        return render(request, 'dashboard/planning.html', {
            'page_title': 'Retirement Planning',
            'error': str(e)
        })

@login_required
def calculate_retirement(request):
    """AJAX endpoint to calculate retirement projections"""
    try:
        # Get data from request
        data = json.loads(request.body)
        current_age = data.get('current_age', 30)
        retirement_age = data.get('retirement_age', 65)
        current_savings = data.get('current_savings', 0)
        monthly_savings = data.get('monthly_savings', 0)
        expected_return = data.get('expected_return', 7) / 100  # Convert from percentage
        
        # Calculate years to retirement
        years_to_retirement = max(0, retirement_age - current_age)
        
        # Fixed inflation rate
        inflation_rate = 0.025  # 2.5%
        
        # Default life expectancy
        life_expectancy = 90
        
        # Simple projection calculations - future value with annual contributions
        projected_savings = calculate_projected_savings(
            current_savings,
            monthly_savings,
            years_to_retirement,
            expected_return
        )
        
        # Calculate retirement years
        retirement_years = life_expectancy - retirement_age
        
        # Calculate target savings needed (25x annual expenses)
        annual_desired_income = 5000 * 12  # Default $5000/month
        target_savings = annual_desired_income * 25
        
        # Calculate retirement progress
        retirement_progress = min(100, int((current_savings / target_savings) * 100)) if target_savings > 0 else 0
        
        # Estimate monthly retirement income (4% rule)
        monthly_retirement_income = (projected_savings * 0.04) / 12
        
        # Generate projection data for chart
        projection_data = {
            'ages': [],
            'savings': [],
            'target': []
        }
        
        running_total = current_savings
        for age in range(current_age, retirement_age + 1):
            projection_data['ages'].append(age)
            projection_data['target'].append(target_savings)
            
            if age > current_age:
                running_total = running_total * (1 + expected_return) + (monthly_savings * 12)
            
            projection_data['savings'].append(round(running_total))
        
        return JsonResponse({
            'success': True,
            'projected_savings': round(projected_savings),
            'monthly_income': round(monthly_retirement_income),
            'progress': retirement_progress,
            'target_savings': round(target_savings),
            'projection_data': projection_data
        })
    except Exception as e:
        logger.error(f"Error in calculate_retirement: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def save_retirement_profile(request):
    """AJAX endpoint to save retirement data to user profile"""
    try:
        # Get data from request
        data = json.loads(request.body)
        retirement_age = data.get('retirement_age', 65)
        current_savings = data.get('current_savings', 0)
        monthly_savings = data.get('monthly_savings', 0)
        expected_return = data.get('expected_return', 7)
        
        # Connect to Supabase
        adapter = SupabaseAdapter()
        
        # Get user's email to identify them
        user_email = request.user.email
        
        # Try to find the user in Supabase by email
        try:
            # Query profiles table by email
            profiles = adapter.client.table('profiles').select('*').eq('email', user_email).execute()
            if profiles.data and len(profiles.data) > 0:
                supabase_id = profiles.data[0]['id']
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'User profile not found in Supabase'
                })
        except Exception as e:
            logger.error(f"Error finding user profile: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error finding user profile: {str(e)}'
            })
        
        # Prepare profile data to update
        profile_data = {
            'retirement_age_goal': retirement_age,
            'current_retirement_savings': current_savings, 
            'monthly_savings_goal': monthly_savings,
            'expected_annual_return': expected_return
        }
        
        # Log what we're trying to save
        logger.info(f"Saving retirement profile data: {profile_data}")
        
        # Update profile in Supabase
        try:
            result = adapter.client.table('profiles').update(profile_data).eq('id', supabase_id).execute()
            if result.data:
                logger.info(f"Profile updated successfully: {result.data}")
                return JsonResponse({
                    'success': True,
                    'message': 'Profile updated successfully!'
                })
            else:
                logger.error("Failed to update profile - no result data")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to update profile'
                })
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error updating profile: {str(e)}'
            })
    except Exception as e:
        logger.error(f"Error in save_retirement_profile: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def calculate_projected_savings(current_savings, monthly_savings, years, expected_return):
    """Calculate projected savings at retirement using compound interest formula"""
    annual_savings = monthly_savings * 12
    
    # Future value of current savings
    future_value = current_savings * (1 + expected_return) ** years
    
    # Future value of regular contributions
    if expected_return > 0:
        future_value_contributions = annual_savings * ((1 + expected_return) ** years - 1) / expected_return
    else:
        future_value_contributions = annual_savings * years
    
    return future_value + future_value_contributions 