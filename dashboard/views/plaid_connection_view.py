"""
Views for Plaid connection and management.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.conf import settings
from supabase_integration.decorators import login_required
from supabase_integration.services import PlaidService
from datetime import datetime, timedelta, timezone as dt_timezone

logger = logging.getLogger(__name__)

@login_required
def connect_bank_view(request):
    """View for connecting bank accounts via Plaid"""
    # Initialize the PlaidService
    plaid_service = PlaidService()
    
    # Get the user's current Plaid connection status
    plaid_status = plaid_service.get_plaid_status(request.user)
    
    # Check if any items need refresh
    refresh_status = plaid_service.check_items_needing_refresh(request.user)
    
    # Prepare context for rendering
    context = {
        'page_title': 'Connect Bank Accounts',
        'plaid_status': plaid_status,
        'refresh_status': refresh_status,
        'is_connected': plaid_status.get('connected', False),
        'days_until_next_hard_refresh': None
    }
    
    # Make sure institution names are set - display placeholder for missing names
    if plaid_status.get('institutions'):
        for inst in plaid_status.get('institutions', []):
            if not inst.get('name'):
                # Try to get from institution_name field
                if inst.get('institution_name'):
                    inst['name'] = inst['institution_name']
                else:
                    # Use a default if no name found
                    inst['name'] = 'Unknown Bank'
    
    # Calculate days until next hard refresh if applicable
    next_hard_refresh = plaid_status.get('next_hard_refresh')
    if next_hard_refresh:
        try:
            next_refresh_date = datetime.fromisoformat(next_hard_refresh.rstrip('Z'))
            # Make sure we're comparing timezone-aware datetimes
            if next_refresh_date.tzinfo is None:
                # If the date has no timezone, assume UTC
                next_refresh_date = next_refresh_date.replace(tzinfo=dt_timezone.utc)
                
            # Use timezone-aware now
            now = datetime.now(dt_timezone.utc)
            days_until = (next_refresh_date - now).days
            context['days_until_next_hard_refresh'] = max(0, days_until)
        except Exception as e:
            logger.error(f"Error calculating days until next refresh: {str(e)}")
            # Set a default value to avoid UI issues
            context['days_until_next_hard_refresh'] = 90
    
    return render(request, 'dashboard/plaid_connection.html', context)

@login_required
@require_http_methods(["GET"])
def create_link_token_view(request):
    """API view to create a Plaid Link token"""
    try:
        # Get query parameters
        update_mode = request.GET.get('update_mode')
        item_id = request.GET.get('item_id')
        
        logger.info(f"Creating Plaid link token - update_mode: {update_mode}, item_id: {item_id}")
        
        # Initialize service
        plaid_service = PlaidService()
        
        # Create link token
        link_token = plaid_service.create_link_token(
            request.user,
            update_mode=update_mode,
            item_id=item_id
        )
        
        if link_token:
            logger.info(f"Successfully created link token: {link_token[:10]}...")
            return JsonResponse({
                'success': True,
                'link_token': link_token
            })
        else:
            logger.error("Link token creation failed - PlaidService returned None")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create link token'
            }, status=400)
    except Exception as e:
        logger.error(f"Exception in create_link_token_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def exchange_public_token_view(request):
    """API view to exchange a public token from Plaid"""
    try:
        # Parse request data
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        public_token = data.get('public_token')
        is_reconnect = data.get('is_reconnect') == 'true'
        existing_item_id = data.get('item_id')
        
        if not public_token:
            logger.error("Missing public token in exchange request")
            return JsonResponse({
                'success': False,
                'error': 'Missing public token'
            }, status=400)
        
        # Log request details
        logger.info(f"Exchanging public token: reconnect={is_reconnect}, item_id={existing_item_id}")
        
        # Initialize service
        plaid_service = PlaidService()
        
        # Exchange token
        try:
            success = plaid_service.exchange_public_token(
                request.user,
                public_token,
                is_reconnect=is_reconnect,
                existing_item_id=existing_item_id
            )
            
            if success:
                # Get updated connection status
                plaid_status = plaid_service.get_plaid_status(request.user)
                
                logger.info(f"Successfully exchanged public token for user {request.user.id}")
                return JsonResponse({
                    'success': True,
                    'message': 'Successfully connected bank account',
                    'plaid_status': plaid_status
                })
            else:
                logger.error(f"Failed to exchange token, PlaidService returned False")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to connect bank account - service error'
                }, status=400)
        except Exception as service_error:
            logger.error(f"Service error exchanging public token: {str(service_error)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Service error: {str(service_error)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in exchange_public_token_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def manual_refresh_view(request):
    """API view to trigger a manual refresh of Plaid data"""
    try:
        # Parse request data
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        refresh_type = data.get('refresh_type', 'soft')
        item_id = data.get('item_id')
        
        logger.info(f"Manual refresh requested for item {item_id}, type: {refresh_type}")
        
        if not item_id:
            logger.error("Missing item_id in refresh request")
            return JsonResponse({
                'success': False,
                'error': 'Missing item_id'
            }, status=400)
        
        # Initialize service
        plaid_service = PlaidService()
        adapter = plaid_service.adapter
        
        # Get the item to refresh
        item = adapter.get_plaid_item_by_id(item_id)
        
        if not item:
            logger.error(f"Item not found: {item_id}")
            return JsonResponse({
                'success': False,
                'error': 'Item not found'
            }, status=404)
        
        # Check if refresh is allowed based on timing restrictions
        now = datetime.now(dt_timezone.utc)
        
        if refresh_type == 'hard':
            # Check hard refresh restrictions (quarterly)
            next_hard_refresh = item.get('next_hard_refresh')
            if next_hard_refresh:
                next_refresh_date = datetime.fromisoformat(next_hard_refresh.rstrip('Z'))
                if next_refresh_date.tzinfo is None:
                    next_refresh_date = next_refresh_date.replace(tzinfo=dt_timezone.utc)
                
                if now < next_refresh_date:
                    # Calculate days until next refresh is allowed
                    days_until = (next_refresh_date - now).days
                    logger.info(f"Hard refresh not allowed yet. Next refresh in {days_until} days")
                    
                    return JsonResponse({
                        'success': False,
                        'error': f'Hard refresh not allowed yet. Please try again in {days_until} days.',
                        'days_until_next_refresh': days_until
                    })
            
            # Hard refresh is allowed - redirect to Plaid Link
            logger.info(f"Hard refresh requested for item {item_id}, redirecting to Plaid Link")
            return JsonResponse({
                'success': True,
                'action': 'redirect',
                'message': 'Please reconnect your account',
                'item_id': item_id
            })
        else:
            # Check soft refresh restrictions (weekly)
            last_successful_update = item.get('last_successful_update')
            if last_successful_update:
                last_update_date = datetime.fromisoformat(last_successful_update.rstrip('Z'))
                if last_update_date.tzinfo is None:
                    last_update_date = last_update_date.replace(tzinfo=dt_timezone.utc)
                
                # Calculate the next allowed refresh date (7 days after last update)
                next_allowed_refresh = last_update_date + timedelta(days=7)
                
                if now < next_allowed_refresh:
                    # Calculate days until next refresh is allowed
                    days_until = max(1, (next_allowed_refresh - now).days)
                    hours_until = int((next_allowed_refresh - now).total_seconds() // 3600)
                    
                    if days_until >= 1:
                        time_message = f"{days_until} days"
                    else:
                        time_message = f"{hours_until} hours"
                    
                    logger.info(f"Soft refresh not allowed yet. Next refresh in {time_message}")
                    
                    return JsonResponse({
                        'success': False,
                        'error': f'Soft refresh not allowed yet. Please try again in {time_message}.',
                        'hours_until_next_refresh': hours_until
                    })
            
            # Soft refresh is allowed - perform it
            logger.info(f"Refreshing accounts for user {request.user.id}, item {item_id}")
            plaid_service.refresh_accounts(request.user)
            
            # Record the refresh
            adapter.record_soft_refresh(item_id)
            
            # Get transactions for the last 90 days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            # Format dates as ISO strings for the API
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            logger.info(f"Syncing transactions from {start_date_str} to {end_date_str}")
            transactions = plaid_service.sync_transactions(request.user, start_date_str, end_date_str)
            logger.info(f"Synced {len(transactions)} transactions")
            
            # Get updated status
            plaid_status = plaid_service.get_plaid_status(request.user)
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully refreshed accounts and synced {len(transactions)} transactions',
                'transaction_count': len(transactions),
                'plaid_status': plaid_status
            })
            
    except Exception as e:
        logger.error(f"Error refreshing Plaid data: {str(e)}")
        logger.exception("Full exception details:")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500) 