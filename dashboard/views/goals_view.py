"""
Views for financial goals functionality.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
import json
from supabase_integration.decorators import login_required
from supabase_integration.adapter import SupabaseAdapter
from supabase_integration.services import SupabaseService
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Mapping from frontend goal types to valid database enum values
GOAL_TYPE_MAPPING = {
    # Direct 1:1 mappings where the enum exists in database
    'emergency': 'emergency',    
    'retirement': 'retirement',  
    'education': 'education',    
    'home': 'home',             # After migration, this will be valid
    'vacation': 'vacation',     # After migration, this will be valid
    'vehicle': 'vehicle',       # After migration, this will be valid
    'investment': 'investment', # After migration, this will be valid
    'wedding': 'wedding',       # After migration, this will be valid
    'health': 'health',         # After migration, this will be valid
    'other': 'other'            # After migration, this will be valid
}

# Fallback mapping for database compatibility before migration is run
FALLBACK_TYPE_MAPPING = {
    'home': 'emergency',
    'vacation': 'emergency',
    'vehicle': 'emergency',
    'investment': 'emergency',
    'wedding': 'emergency',
    'health': 'emergency',
    'other': 'emergency'
}

# Reverse mapping for displaying goal types
REVERSE_GOAL_TYPE_MAPPING = {
    'emergency': ['emergency'],
    'retirement': ['retirement'],
    'education': ['education'],
    'home': ['home'],
    'vacation': ['vacation'],
    'vehicle': ['vehicle'],
    'investment': ['investment'],
    'wedding': ['wedding'],
    'health': ['health'],
    'other': ['other']
}

def map_goal_type_to_valid_enum(goal_type):
    """Map a frontend goal type to a valid database enum value"""
    # If type is directly in the mapping, try to use it
    if goal_type in GOAL_TYPE_MAPPING:
        db_type = GOAL_TYPE_MAPPING[goal_type]
        
        try:
            # Try to use the direct mapping
            return db_type
        except Exception as e:
            # If we get an error (e.g., invalid enum value), use fallback
            logger.warning(f"Error using direct goal type mapping for {goal_type}: {str(e)}")
            if goal_type in FALLBACK_TYPE_MAPPING:
                return FALLBACK_TYPE_MAPPING[goal_type]
            return 'emergency'  # Ultimate fallback
    
    # Default to 'emergency' for any unmapped types
    logger.warning(f"Unknown goal type: {goal_type}, mapping to 'emergency'")
    return 'emergency'

@login_required
def goals_view(request):
    """View for managing financial goals"""
    try:
        # Get the user's Supabase ID directly from the user object
        # The user.id is the Django user ID, which should match the Supabase ID
        # when properly integrated
        supabase_id = request.user.id
        
        if not supabase_id:
            messages.error(request, "Your account is not properly connected. Please contact support.")
            return redirect('dashboard:dashboard')
        
        # Get user's goals from Supabase
        adapter = SupabaseAdapter()
        goals = adapter.client.table('financial_goals').select('*').eq('user_id', supabase_id).order('created_at').execute()
        
        # Calculate the overall progress
        goals_data = goals.data if hasattr(goals, 'data') else []
        
        # Initialize default values in case of empty data
        total_target = 0
        total_current = 0
        overall_progress = 0
        
        if goals_data:
            total_target = sum(goal.get('target_amount', 0) for goal in goals_data)
            total_current = sum(goal.get('current_amount', 0) for goal in goals_data)
            overall_progress = int((total_current / total_target * 100) if total_target > 0 else 0)
        
        # Process goals to add formatted data
        for goal in goals_data:
            # Ensure all required fields exist with defaults
            if 'target_amount' not in goal:
                goal['target_amount'] = 0
            if 'current_amount' not in goal:
                goal['current_amount'] = 0
                
            # For frontend display purposes, infer the frontend goal type
            if 'goal_type' in goal:
                db_goal_type = goal['goal_type']
                # Default to the same type if no mapping exists
                goal['frontend_goal_type'] = db_goal_type
                
                # Try to find a better frontend type based on the name or other factors
                for frontend_type, db_types in REVERSE_GOAL_TYPE_MAPPING.items():
                    if db_goal_type in db_types:
                        # For emergency, try to determine if it's a home goal based on name
                        if db_goal_type == 'emergency' and 'name' in goal:
                            name_lower = goal['name'].lower()
                            if 'home' in name_lower or 'house' in name_lower or 'down payment' in name_lower:
                                goal['frontend_goal_type'] = 'home'
                                break
                        
                        # For "other" types, try to be more specific based on name
                        if db_goal_type == 'other' and 'name' in goal:
                            name_lower = goal['name'].lower()
                            for possible_type in ['vacation', 'vehicle', 'car', 'investment', 'wedding', 'health']:
                                if possible_type in name_lower:
                                    goal['frontend_goal_type'] = possible_type
                                    break
                
            # Calculate progress percentage
            if goal.get('target_amount', 0) > 0:
                goal['progress_percentage'] = min(
                    round((goal.get('current_amount', 0) / goal.get('target_amount', 0)) * 100),
                    100
                )
            else:
                goal['progress_percentage'] = 0
                
            # Format target date
            if goal.get('target_date'):
                try:
                    goal['formatted_target_date'] = goal['target_date'].split('T')[0]  # Extract just the date part
                    
                    # Calculate months remaining
                    target_date = datetime.fromisoformat(goal['target_date'].replace('Z', '+00:00'))
                    now = datetime.now()
                    months_remaining = (target_date.year - now.year) * 12 + (target_date.month - now.month)
                    
                    if months_remaining <= 0:
                        goal['time_remaining'] = 'Past due'
                    elif months_remaining < 12:
                        goal['time_remaining'] = f"{months_remaining} mo"
                    else:
                        years = months_remaining // 12
                        goal['time_remaining'] = f"{years} yr{'' if years == 1 else 's'}"
                except (ValueError, IndexError, TypeError) as date_error:
                    logger.warning(f"Error processing target date: {date_error}")
                    goal['formatted_target_date'] = None
                    goal['time_remaining'] = '--'
            else:
                goal['formatted_target_date'] = None
                goal['time_remaining'] = '--'
            
            # Determine status
            if goal.get('progress_percentage', 0) == 100:
                goal['status_class'] = 'status-completed'
                goal['status_text'] = 'Completed'
            elif goal.get('progress_percentage', 0) >= 85:
                goal['status_class'] = 'status-on-track'
                goal['status_text'] = 'On Track'
            elif goal.get('progress_percentage', 0) >= 50:
                goal['status_class'] = 'status-at-risk'
                goal['status_text'] = 'At Risk'
            else:
                goal['status_class'] = 'status-behind'
                goal['status_text'] = 'Behind'
        
        context = {
            'page_title': 'Financial Goals',
            'goals': goals_data,
            'overall_progress': overall_progress,
            'active_goals_count': len(goals_data),
            'total_saved': total_current,
            'goal_types': json.dumps(GOAL_TYPE_MAPPING)  # Pass mapping to frontend
        }
        
        return render(request, 'dashboard/goals.html', context)
    except Exception as e:
        logger.error(f"Error in goals view: {str(e)}")
        # Instead of redirecting, render the goals page with an error message
        context = {
            'page_title': 'Financial Goals',
            'goals': [],
            'overall_progress': 0,
            'active_goals_count': 0,
            'total_saved': 0,
            'error_message': f"We encountered an issue loading your goals. Please try again later."
        }
        messages.error(request, "We encountered an issue loading your goals. Please try again later.")
        return render(request, 'dashboard/goals.html', context)

@login_required
@require_http_methods(["POST"])
def create_goal(request):
    """API endpoint to create a new financial goal"""
    try:
        # Add request debugging information
        request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{id(request)}"
        logger.info(f"[{request_id}] Starting goal creation request")
        
        # Get the user's Supabase ID directly
        supabase_id = request.user.id
        
        if not supabase_id:
            logger.warning(f"[{request_id}] User not found or no supabase_id")
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Parse request data
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        # Validate required fields
        required_fields = ['name', 'goal_type', 'target_amount']
        for field in required_fields:
            if field not in data:
                logger.warning(f"[{request_id}] Missing required field: {field}")
                return JsonResponse({'success': False, 'error': f'Missing required field: {field}'}, status=400)
        
        # Extract key data from request
        goal_name = data.get('name')
        frontend_goal_type = data.get('goal_type')
        target_amount = float(data.get('target_amount'))
        current_amount = float(data.get('current_amount', 0))
        
        # Map the goal type to a valid database enum value
        db_goal_type = map_goal_type_to_valid_enum(frontend_goal_type)
        
        # Create a unique client-side ID to detect duplicates more reliably
        client_request_id = data.get('client_request_id')
        if not client_request_id:
            # Generate a request ID if not provided
            client_request_id = f"gen-{request_id}"
        
        logger.info(f"[{request_id}] Processing goal '{goal_name}' with client_request_id: {client_request_id}")
        
        # Check for duplicates with the exact same parameters in the recent past
        # This is a more exact check than just name matching
        adapter = SupabaseAdapter()
        
        # First check for an existing goal with the same client_request_id in metadata
        # This is the most reliable way to detect a duplicate submission
        try:
            # Use RPC to check for client_request_id in metadata
            check_by_request_id = adapter.client.rpc(
                'find_goal_by_client_request_id',
                {
                    'p_user_id': supabase_id,
                    'p_client_request_id': client_request_id,
                    'p_minutes': 10  # Look back 10 minutes
                }
            ).execute()
            
            if check_by_request_id.data and len(check_by_request_id.data) > 0:
                goal = check_by_request_id.data[0]
                logger.warning(f"[{request_id}] Duplicate goal detected by client_request_id: {client_request_id}")
                return JsonResponse({
                    'success': True, 
                    'goal': goal,
                    'message': 'Goal already exists',
                    'duplicate': True
                })
        except Exception as e:
            # If the RPC fails, log it but continue with other checks
            logger.warning(f"[{request_id}] Error checking for duplicate by client_request_id: {str(e)}")
        
        # Fallback: Check by name, type, and amounts for recent goals
        thirty_seconds_ago = (datetime.now() - timedelta(seconds=30)).isoformat()
        check_duplicates = adapter.client.table('financial_goals') \
            .select('*') \
            .eq('user_id', supabase_id) \
            .eq('name', goal_name) \
            .eq('goal_type', db_goal_type) \
            .gte('created_at', thirty_seconds_ago) \
            .execute()
        
        if check_duplicates.data and len(check_duplicates.data) > 0:
            # Found a potential duplicate with the same name, type, and within 30 seconds
            logger.warning(f"[{request_id}] Potential duplicate goal detected with name '{goal_name}' created within 30 seconds")
            
            # Verify amounts are similar (floating point comparison with tolerance)
            for existing_goal in check_duplicates.data:
                if (abs(existing_goal.get('target_amount', 0) - target_amount) < 0.01 and
                    abs(existing_goal.get('current_amount', 0) - current_amount) < 0.01):
                    
                    logger.warning(f"[{request_id}] Confirmed duplicate with matching amounts: {existing_goal['id']}")
                    return JsonResponse({
                        'success': True, 
                        'goal': existing_goal,
                        'message': 'Goal already exists',
                        'duplicate': True
                    })
        
        # If we got here, no exact duplicate was found
        logger.info(f"[{request_id}] No duplicate found, creating new goal")
        
        # Add metadata with client_request_id to detect duplicates in the future
        metadata = {
            'client_request_id': client_request_id,
            'created_from': 'web',
            'request_id': request_id,
            'frontend_goal_type': frontend_goal_type
        }
        
        # Prepare goal data
        goal_data = {
            'user_id': supabase_id,
            'name': goal_name,
            'goal_type': db_goal_type,  # Use the mapped value
            'target_amount': target_amount,
            'current_amount': current_amount,
            'metadata': metadata  # Store additional data for duplicate detection
        }
        
        # Add optional fields if present
        if 'target_date' in data and data['target_date']:
            goal_data['target_date'] = data['target_date']
        
        if 'description' in data:
            goal_data['description'] = data['description']
        
        # Insert goal into Supabase
        logger.info(f"[{request_id}] Inserting goal into database: {goal_data}")
        response = adapter.client.table('financial_goals').insert(goal_data).execute()
        
        if response.data:
            # Add the frontend goal type to the response for UI consistency
            response.data[0]['frontend_goal_type'] = frontend_goal_type
            logger.info(f"[{request_id}] Goal created successfully with ID: {response.data[0].get('id')}")
            return JsonResponse({'success': True, 'goal': response.data[0]})
        else:
            logger.error(f"[{request_id}] Failed to create goal: No data returned from insert")
            return JsonResponse({'success': False, 'error': 'Failed to create goal'}, status=500)
            
    except Exception as e:
        logger.error(f"Error creating goal: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def update_goal(request, goal_id):
    """API endpoint to update an existing financial goal"""
    try:
        # Get the user's Supabase ID directly
        supabase_id = request.user.id
        
        if not supabase_id:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Parse request data
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        # Prepare update data
        update_data = {}
        
        # Only include fields that are present in the request
        updateable_fields = ['name', 'target_amount', 'current_amount', 
                            'target_date', 'description']
        
        for field in updateable_fields:
            if field in data:
                update_data[field] = data[field]
                
                # Convert amount fields to float
                if field in ['target_amount', 'current_amount']:
                    update_data[field] = float(data[field])
        
        # Handle goal_type separately with the mapping
        if 'goal_type' in data:
            frontend_goal_type = data.get('goal_type')
            update_data['goal_type'] = map_goal_type_to_valid_enum(frontend_goal_type)
            
        # Update goal in Supabase
        adapter = SupabaseAdapter()
        
        # First verify the goal belongs to this user
        verify = adapter.client.table('financial_goals').select('id').eq('id', goal_id).eq('user_id', supabase_id).execute()
        
        if not verify.data:
            return JsonResponse({'success': False, 'error': 'Goal not found or access denied'}, status=403)
        
        # Perform the update
        response = adapter.client.table('financial_goals').update(update_data).eq('id', goal_id).execute()
        
        if response.data:
            # Add the frontend goal type to the response for UI consistency
            if 'goal_type' in data:
                response.data[0]['frontend_goal_type'] = data.get('goal_type')
            return JsonResponse({'success': True, 'goal': response.data[0]})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to update goal'}, status=500)
            
    except Exception as e:
        logger.error(f"Error updating goal: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def delete_goal(request, goal_id):
    """API endpoint to delete a financial goal"""
    try:
        # Get the user's Supabase ID directly
        supabase_id = request.user.id
        
        if not supabase_id:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Verify the goal belongs to this user
        adapter = SupabaseAdapter()
        verify = adapter.client.table('financial_goals').select('id').eq('id', goal_id).eq('user_id', supabase_id).execute()
        
        if not verify.data:
            return JsonResponse({'success': False, 'error': 'Goal not found or access denied'}, status=403)
        
        # Delete the goal
        response = adapter.client.table('financial_goals').delete().eq('id', goal_id).execute()
        
        return JsonResponse({'success': True})
            
    except Exception as e:
        logger.error(f"Error deleting goal: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def add_funds(request, goal_id):
    """API endpoint to add funds to a goal"""
    try:
        # Get the user's Supabase ID directly
        supabase_id = request.user.id
        
        if not supabase_id:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Parse request data
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        # Validate amount
        if 'amount' not in data:
            return JsonResponse({'success': False, 'error': 'Amount is required'}, status=400)
        
        amount = float(data.get('amount', 0))
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Amount must be positive'}, status=400)
        
        adapter = SupabaseAdapter()
        
        # Verify the goal belongs to this user
        verify = adapter.client.table('financial_goals').select('id').eq('id', goal_id).eq('user_id', supabase_id).execute()
        
        if not verify.data:
            return JsonResponse({'success': False, 'error': 'Goal not found or access denied'}, status=403)
        
        # Add transaction record
        transaction_data = {
            'goal_id': goal_id,
            'amount': amount,
            'transaction_type': 'deposit',
            'notes': data.get('notes', '')
        }
        
        # Start transaction
        # Insert transaction record
        transaction_response = adapter.client.table('goal_transactions').insert(transaction_data).execute()
        
        if not transaction_response.data:
            return JsonResponse({'success': False, 'error': 'Failed to record transaction'}, status=500)
        
        # Get updated goal data
        goal_response = adapter.client.table('financial_goals').select('*').eq('id', goal_id).execute()
        
        if goal_response.data:
            return JsonResponse({'success': True, 'goal': goal_response.data[0], 'transaction': transaction_response.data[0]})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to retrieve updated goal'}, status=500)
            
    except Exception as e:
        logger.error(f"Error adding funds: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500) 