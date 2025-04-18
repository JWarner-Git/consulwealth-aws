"""
Mobile API views for Plaid integration.
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from supabase_integration.services import PlaidService
from supabase_integration.decorators import jwt_auth_required

logger = logging.getLogger(__name__)

@csrf_exempt
@jwt_auth_required
@require_http_methods(["POST"])
def create_link_token(request):
    """
    Mobile API endpoint to create a Plaid Link token
    """
    try:
        # Extract user ID from the authenticated request
        user = request.user
        
        # Initialize the PlaidService
        plaid_service = PlaidService()
        
        # Create link token
        link_token = plaid_service.create_link_token(user)
        
        if link_token:
            logger.info(f"Successfully created link token for mobile: {link_token[:10]}...")
            return JsonResponse({
                'success': True,
                'link_token': link_token
            })
        else:
            logger.error("Mobile link token creation failed - PlaidService returned None")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create link token'
            }, status=400)
    except Exception as e:
        logger.error(f"Exception in mobile create_link_token: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@jwt_auth_required
@require_http_methods(["POST"])
def exchange_public_token(request):
    """
    Mobile API endpoint to exchange a public token from Plaid
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        
        public_token = data.get('public_token')
        is_reconnect = data.get('is_reconnect', False)
        existing_item_id = data.get('item_id')
        
        if not public_token:
            logger.error("Missing public token in mobile exchange request")
            return JsonResponse({
                'success': False,
                'error': 'Missing public token'
            }, status=400)
        
        # Log request details
        logger.info(f"Mobile: Exchanging public token: reconnect={is_reconnect}, item_id={existing_item_id}")
        
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
                
                logger.info(f"Successfully exchanged public token for mobile user {request.user.id}")
                return JsonResponse({
                    'success': True,
                    'message': 'Successfully connected bank account',
                    'plaid_status': plaid_status
                })
            else:
                logger.error(f"Failed to exchange token for mobile, PlaidService returned False")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to connect bank account - service error'
                }, status=400)
        except Exception as service_error:
            logger.error(f"Service error exchanging public token for mobile: {str(service_error)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Service error: {str(service_error)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in mobile exchange_public_token: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@jwt_auth_required
@require_http_methods(["GET"])
def get_plaid_items(request):
    """
    Mobile API endpoint to get user's Plaid items
    """
    try:
        # Initialize the PlaidService
        plaid_service = PlaidService()
        
        # Get the user's Plaid items
        adapter = plaid_service.adapter
        items = adapter.get_plaid_items(request.user)
        
        return JsonResponse({
            'success': True,
            'plaid_items': items
        })
    except Exception as e:
        logger.error(f"Error in mobile get_plaid_items: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@jwt_auth_required
@require_http_methods(["GET"])
def get_accounts(request):
    """
    Mobile API endpoint to get user's financial accounts
    """
    try:
        # Initialize the PlaidService
        plaid_service = PlaidService()
        
        # Get the user's accounts
        adapter = plaid_service.adapter
        accounts = adapter.get_accounts(request.user)
        
        return JsonResponse({
            'success': True,
            'accounts': accounts
        })
    except Exception as e:
        logger.error(f"Error in mobile get_accounts: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@jwt_auth_required
@require_http_methods(["GET"])
def get_transactions(request):
    """
    Mobile API endpoint to get user's transactions
    """
    try:
        # Get query parameters for filtering
        start_date = request.GET.get('start_date')  # Format: YYYY-MM-DD
        end_date = request.GET.get('end_date')      # Format: YYYY-MM-DD
        account_id = request.GET.get('account_id')  # Optional account ID for filtering
        
        # Initialize the PlaidService
        plaid_service = PlaidService()
        
        # Get the user's transactions
        adapter = plaid_service.adapter
        transactions = adapter.get_transactions(
            request.user.id,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id
        )
        
        return JsonResponse({
            'success': True,
            'transactions': transactions
        })
    except Exception as e:
        logger.error(f"Error in mobile get_transactions: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@jwt_auth_required
@require_http_methods(["POST"])
def manual_refresh(request):
    """
    Mobile API endpoint to manually refresh Plaid data
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        
        item_id = data.get('item_id')
        refresh_type = data.get('refresh_type', 'soft')  # Default to soft refresh
        
        if not item_id:
            logger.error("Missing item_id in mobile refresh request")
            return JsonResponse({
                'success': False,
                'error': 'Missing item_id'
            }, status=400)
        
        # Initialize service
        plaid_service = PlaidService()
        adapter = plaid_service.adapter
        
        # Verify the item belongs to this user
        item = adapter.get_plaid_item_by_id(item_id)
        if not item or str(item.get('user_id')) != str(request.user.id):
            logger.error(f"User {request.user.id} attempted to refresh item {item_id} which doesn't belong to them")
            return JsonResponse({
                'success': False,
                'error': 'Item not found or unauthorized'
            }, status=403)
        
        # Perform the refresh
        success = False
        if refresh_type.lower() == 'hard':
            success = adapter.record_hard_refresh(item_id)
        else:
            success = adapter.record_soft_refresh(item_id)
        
        if success:
            logger.info(f"Successfully initiated {refresh_type} refresh for item {item_id}")
            return JsonResponse({
                'success': True,
                'message': f'{refresh_type.capitalize()} refresh initiated successfully'
            })
        else:
            logger.error(f"Failed to initiate {refresh_type} refresh for item {item_id}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to initiate {refresh_type} refresh'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error in mobile manual_refresh: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500) 