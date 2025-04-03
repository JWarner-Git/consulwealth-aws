from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import logging
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from datetime import datetime, timedelta
import requests
import os

logger = logging.getLogger(__name__)

# ----- PLAID CONFIGURATION -----
PLAID_CLIENT_ID = settings.PLAID_CLIENT_ID
PLAID_SECRET = settings.PLAID_SECRET
PLAID_ENV = settings.PLAID_ENVIRONMENT
PLAID_PRODUCTS = ['auth', 'transactions']
PLAID_COUNTRY_CODES = ['US']
PLAID_REDIRECT_URI = None

@login_required
def create_link_token(request):
    """
    Create a link token using the Plaid API
    Uses the official Plaid API directly via requests instead of SDK to avoid compatibility issues
    """
    try:
        logger.info(f"Creating link token for user {request.user.id} in {PLAID_ENV} environment")
        
        # Based on the environment, use the appropriate API URL
        if PLAID_ENV == 'sandbox':
            plaid_api_host = 'https://sandbox.plaid.com'
        elif PLAID_ENV == 'development':
            plaid_api_host = 'https://development.plaid.com'
        elif PLAID_ENV == 'production':
            plaid_api_host = 'https://production.plaid.com'
        else:
            logger.error(f"Invalid Plaid environment: {PLAID_ENV}")
            return JsonResponse({'error': 'Invalid Plaid environment'}, status=400)
            
        # User ID must be a string for Plaid
        client_user_id = str(request.user.id)
        
        # Build the request payload
        payload = {
            'client_id': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
            'client_name': 'ConsulWealth App',
            'user': {
                'client_user_id': client_user_id
            },
            'products': PLAID_PRODUCTS,
            'country_codes': PLAID_COUNTRY_CODES,
            'language': 'en'
        }
        
        if PLAID_REDIRECT_URI:
            payload['redirect_uri'] = PLAID_REDIRECT_URI
            
        # Make the API request
        response = requests.post(
            f'{plaid_api_host}/link/token/create',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        # Handle the response
        if response.status_code == 200:
            data = response.json()
            link_token = data.get('link_token')
            logger.info(f"Successfully created link token: {link_token[:10]}...")
            return JsonResponse({'link_token': link_token})
        else:
            error_message = f"Plaid API error: {response.status_code} - {response.text}"
            logger.error(error_message)
            return JsonResponse({'error': error_message}, status=400)
            
    except Exception as e:
        logger.error(f"Error creating link token: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def exchange_public_token(request):
    """
    Exchange a public token for an access token using the Plaid API
    This is called after a user successfully connects their bank account
    """
    try:
        # Parse the request body
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        # Get the public token
        public_token = data.get('public_token')
        
        if not public_token:
            logger.error("No public token provided")
            return JsonResponse({'error': 'No public token provided'}, status=400)
            
        logger.info(f"Exchanging public token (first 10 chars): {public_token[:10]}...")
        
        # Exchange the public token for an access token
        if PLAID_ENV == 'sandbox':
            plaid_api_host = 'https://sandbox.plaid.com'
        elif PLAID_ENV == 'development':
            plaid_api_host = 'https://development.plaid.com'
        elif PLAID_ENV == 'production':
            plaid_api_host = 'https://production.plaid.com'
        else:
            logger.error(f"Invalid Plaid environment: {PLAID_ENV}")
            return JsonResponse({'error': 'Invalid Plaid environment'}, status=400)
            
        # Make the API request to exchange the token
        response = requests.post(
            f'{plaid_api_host}/item/public_token/exchange',
            json={
                'client_id': PLAID_CLIENT_ID,
                'secret': PLAID_SECRET,
                'public_token': public_token
            },
            headers={'Content-Type': 'application/json'}
        )
        
        # Handle the response
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            item_id = data.get('item_id')
            
            if not access_token or not item_id:
                logger.error("Missing access_token or item_id in Plaid response")
                return JsonResponse({'error': 'Invalid Plaid response'}, status=400)
                
            logger.info(f"Successfully exchanged public token for access token. Item ID: {item_id[:10]}...")
            
            # Store the access token and item_id directly in Supabase
            from supabase_integration.client import get_supabase_client
            from supabase_integration.adapter import SupabaseAdapter
            
            try:
                # Get the user's Supabase ID directly from Supabase using their email
                # This eliminates the need for the SupabaseSync table
                adapter = SupabaseAdapter()
                
                # Get the current user's email
                user_email = request.user.email
                
                # Get the Supabase user ID by email
                supabase_user = adapter.client.rpc('get_user_by_email', {'email': user_email}).execute()
                
                if not supabase_user.data or len(supabase_user.data) == 0:
                    logger.error(f"No Supabase user found with email: {user_email}")
                    return JsonResponse({
                        'success': False,
                        'error': 'User not found in Supabase'
                    }, status=400)
                
                # Extract the Supabase user ID
                supabase_id = supabase_user.data[0]['id']
                
                # Store the item in Supabase
                result = adapter.store_plaid_item(supabase_id, item_id, access_token)
                
                if result:
                    logger.info(f"Successfully stored Plaid item in Supabase")
                    
                    # Now fetch accounts and sync them
                    try:
                        accounts = fetch_accounts(access_token, supabase_id)
                        logger.info(f"Synced {len(accounts)} accounts")
                        
                        try:
                            # Get transactions for the last 30 days
                            end_date = datetime.now().date()
                            start_date = end_date - timedelta(days=30)
                            
                            transactions = fetch_transactions(access_token, start_date, end_date, accounts)
                            logger.info(f"Synced {len(transactions)} transactions")
                            
                            return JsonResponse({
                                'success': True,
                                'message': 'Successfully connected to Plaid',
                                'accounts_count': len(accounts),
                                'transactions_count': len(transactions)
                            })
                        except Exception as e:
                            logger.error(f"Error syncing transactions: {str(e)}")
                            return JsonResponse({
                                'success': True,
                                'message': 'Connected to Plaid, but error syncing transactions',
                                'accounts_count': len(accounts),
                                'error_details': str(e)
                            })
                    except Exception as e:
                        logger.error(f"Error syncing accounts: {str(e)}")
                        return JsonResponse({
                            'success': True,
                            'message': 'Connected to Plaid, but error syncing accounts',
                            'error_details': str(e)
                        })
                else:
                    logger.error("Failed to store Plaid item in Supabase")
                    return JsonResponse({
                        'success': False,
                        'error': 'Failed to store Plaid item'
                    }, status=500)
            except Exception as e:
                logger.error(f"Error storing Plaid item: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
        else:
            error_message = f"Plaid API error: {response.status_code} - {response.text}"
            logger.error(error_message)
            return JsonResponse({'error': error_message}, status=400)
    except Exception as e:
        logger.error(f"Error exchanging public token: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def fetch_accounts(access_token, supabase_id):
    """
    Fetch accounts from Plaid and store them directly in Supabase
    """
    from supabase_integration.adapter import SupabaseAdapter
    adapter = SupabaseAdapter()
    
    # Get the Plaid API host
    if PLAID_ENV == 'sandbox':
        plaid_api_host = 'https://sandbox.plaid.com'
    elif PLAID_ENV == 'development':
        plaid_api_host = 'https://development.plaid.com'
    elif PLAID_ENV == 'production':
        plaid_api_host = 'https://production.plaid.com'
    else:
        raise ValueError(f"Invalid Plaid environment: {PLAID_ENV}")
    
    # Make API request to get accounts
    response = requests.post(
        f'{plaid_api_host}/accounts/get',
        json={
            'client_id': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
            'access_token': access_token
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        raise Exception(f"Plaid API error: {response.status_code} - {response.text}")
    
    data = response.json()
    accounts = data.get('accounts', [])
    
    # Fetch institution data
    item = data.get('item', {})
    institution_id = item.get('institution_id')
    
    # If we have an institution ID, fetch institution data and store it
    institution_db_id = None
    if institution_id:
        # Fetch institution data from Plaid
        inst_response = requests.post(
            f'{plaid_api_host}/institutions/get_by_id',
            json={
                'client_id': PLAID_CLIENT_ID,
                'secret': PLAID_SECRET,
                'institution_id': institution_id,
                'country_codes': PLAID_COUNTRY_CODES
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if inst_response.status_code == 200:
            inst_data = inst_response.json()
            institution = inst_data.get('institution', {})
            
            # Store institution in Supabase
            institution_data = {
                'institution_id': institution_id,
                'name': institution.get('name', 'Unknown'),
                'logo': institution.get('logo', '')
            }
            
            # Check if institution exists in Supabase
            existing_inst = adapter.client.table('institutions').select('id').eq('institution_id', institution_id).execute()
            
            if existing_inst.data and len(existing_inst.data) > 0:
                institution_db_id = existing_inst.data[0]['id']
            else:
                # Create a new institution
                inst_response = adapter.client.table('institutions').insert(institution_data).execute()
                if inst_response.data and len(inst_response.data) > 0:
                    institution_db_id = inst_response.data[0]['id']
    
    # Store accounts in Supabase
    stored_accounts = []
    for account in accounts:
        account_data = {
            'user_id': supabase_id,
            'institution_id': institution_db_id,
            'account_id': account.get('account_id'),
            'name': account.get('name'),
            'type': account.get('type'),
            'subtype': account.get('subtype', ''),
            'current_balance': account.get('balances', {}).get('current', 0),
            'available_balance': account.get('balances', {}).get('available', 0)
        }
        
        # Check if account exists in Supabase
        existing_account = adapter.client.table('accounts').select('id').eq('account_id', account.get('account_id')).execute()
        
        if existing_account.data and len(existing_account.data) > 0:
            # Update existing account
            account_id = existing_account.data[0]['id']
            account_response = adapter.client.table('accounts').update(account_data).eq('id', account_id).execute()
            if account_response.data and len(account_response.data) > 0:
                stored_accounts.append(account_response.data[0])
        else:
            # Create new account
            account_response = adapter.client.table('accounts').insert(account_data).execute()
            if account_response.data and len(account_response.data) > 0:
                stored_accounts.append(account_response.data[0])
    
    return stored_accounts

def fetch_transactions(access_token, start_date, end_date, accounts):
    """
    Fetch transactions from Plaid and store them directly in Supabase
    """
    from supabase_integration.client import get_supabase_client
    supabase = get_supabase_client()
    
    # Get the Plaid API host
    if PLAID_ENV == 'sandbox':
        plaid_api_host = 'https://sandbox.plaid.com'
    elif PLAID_ENV == 'development':
        plaid_api_host = 'https://development.plaid.com'
    elif PLAID_ENV == 'production':
        plaid_api_host = 'https://production.plaid.com'
    else:
        raise ValueError(f"Invalid Plaid environment: {PLAID_ENV}")
    
    # Format dates as strings
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Make API request to get transactions
    response = requests.post(
        f'{plaid_api_host}/transactions/get',
        json={
            'client_id': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
            'access_token': access_token,
            'start_date': start_date_str,
            'end_date': end_date_str
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        raise Exception(f"Plaid API error: {response.status_code} - {response.text}")
    
    data = response.json()
    transactions = data.get('transactions', [])
    
    # Create a map of account_ids to database IDs
    account_map = {}
    for account in accounts:
        if isinstance(account, dict) and 'account_id' in account and 'id' in account:
            account_map[account['account_id']] = account['id']
    
    # If account_map is empty, we need to get the accounts from Supabase
    if not account_map:
        logger.info("No account mapping provided, fetching from Supabase...")
        plaid_account_ids = [t.get('account_id') for t in transactions]
        
        # Get all accounts matching these Plaid account IDs
        if plaid_account_ids:
            account_response = supabase.table('accounts').select('id, account_id').in_('account_id', plaid_account_ids).execute()
            if account_response.data:
                for acc in account_response.data:
                    account_map[acc['account_id']] = acc['id']
    
    # Prepare transactions for storage
    transaction_data_list = []
    stored_transactions = []
    
    for transaction in transactions:
        plaid_account_id = transaction.get('account_id')
        account_id = account_map.get(plaid_account_id)
        
        if account_id:
            transaction_data = {
                'account_id': account_id,
                'transaction_id': transaction.get('transaction_id'),
                'amount': transaction.get('amount'),
                'date': transaction.get('date'),
                'merchant_name': transaction.get('merchant_name', ''),
                'description': transaction.get('name', ''),  # Use transaction name as description
                'category': transaction.get('category', [''])[0] if transaction.get('category') else '',
                'pending': transaction.get('pending', False)
            }
            transaction_data_list.append(transaction_data)
    
    # Store transactions in batches to avoid large payloads
    batch_size = 50
    for i in range(0, len(transaction_data_list), batch_size):
        batch = transaction_data_list[i:i+batch_size]
        
        if batch:
            # For each transaction, check if it exists and update it, or insert it
            for txn_data in batch:
                # Check if transaction exists
                txn_id = txn_data['transaction_id']
                existing_txn = supabase.table('transactions').select('id').eq('transaction_id', txn_id).execute()
                
                if existing_txn.data and len(existing_txn.data) > 0:
                    # Update existing transaction
                    txn_db_id = existing_txn.data[0]['id']
                    txn_response = supabase.table('transactions').update(txn_data).eq('id', txn_db_id).execute()
                    if txn_response.data:
                        stored_transactions.extend(txn_response.data)
                else:
                    # Insert new transaction
                    txn_response = supabase.table('transactions').insert(txn_data).execute()
                    if txn_response.data:
                        stored_transactions.extend(txn_response.data)
    
    return stored_transactions

@login_required
def simple_plaid_link(request):
    """
    Simple Plaid Link integration page with modern v2 SDK
    """
    try:
        # Create a link token
        response = create_link_token(request)
        
        # If successful, get the link token from the response
        if isinstance(response, JsonResponse):
            data = json.loads(response.content)
            if 'link_token' in data:
                link_token = data['link_token']
            else:
                link_token = None
                messages.error(request, f"Error: {data.get('error', 'Unknown error')}")
        else:
            link_token = None
            messages.error(request, "Error creating link token")
        
        # Check if user already has connected accounts - directly using Supabase
        from supabase_integration.client import get_supabase_client
        from supabase_integration.adapter import SupabaseAdapter
        
        is_connected = False
        accounts_count = 0
        transactions_count = 0
        
        try:
            # Get the current user's email
            user_email = request.user.email
            
            # Initialize the adapter
            adapter = SupabaseAdapter()
            
            # Get the Supabase user ID by email
            supabase_user = adapter.client.rpc('get_user_by_email', {'email': user_email}).execute()
            
            if supabase_user.data and len(supabase_user.data) > 0:
                # Extract the Supabase user ID
                supabase_id = supabase_user.data[0]['id']
                
                # Check for Plaid items directly in Supabase
                plaid_items_response = adapter.client.table('plaid_items').select('id').eq('user_id', supabase_id).execute()
                plaid_items = plaid_items_response.data if plaid_items_response.data else []
                
                if plaid_items:
                    is_connected = True
                    
                    # Get accounts count
                    accounts_response = adapter.client.table('accounts').select('id').eq('user_id', supabase_id).execute()
                    accounts = accounts_response.data if accounts_response.data else []
                    accounts_count = len(accounts)
                    
                    # Get transactions count if accounts exist
                    if accounts:
                        account_ids = [account['id'] for account in accounts]
                        end_date = datetime.now().date().isoformat()
                        start_date = (datetime.now().date() - timedelta(days=30)).isoformat()
                        
                        transactions_response = adapter.client.table('transactions').select('id').in_('account_id', account_ids).gte('date', start_date).lte('date', end_date).execute()
                        transactions = transactions_response.data if transactions_response.data else []
                        transactions_count = len(transactions)
        except Exception as e:
            logger.warning(f"Error checking Plaid connection status: {str(e)}")
        
        # Render the template
        return render(request, 'users/simple_plaid.html', {
            'link_token': link_token,
            'plaid_environment': PLAID_ENV,
            'is_connected': is_connected,
            'accounts_count': accounts_count,
            'transactions_count': transactions_count
        })
    except Exception as e:
        logger.error(f"Error in simple_plaid_link: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('dashboard:dashboard')

@login_required
def standalone_plaid_test(request):
    """Standalone Plaid test page for debugging"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Standalone Plaid Test</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                padding: 20px; 
                max-width: 800px; 
                margin: 0 auto;
                line-height: 1.6;
            }
            .container {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            button {
                background-color: #2c5282;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                margin-right: 10px;
            }
            button:hover {
                background-color: #1a365d;
            }
            #log {
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                height: 300px;
                overflow: auto;
                margin-top: 20px;
                font-family: monospace;
            }
            h1, h2 {
                color: #2c5282;
            }
            pre {
                white-space: pre-wrap;
                word-break: break-all;
            }
            .info-box {
                background-color: #e8f4fd;
                border-left: 4px solid #2c5282;
                padding: 15px;
                margin: 15px 0;
            }
            .error {
                color: red;
            }
        </style>
    </head>
    <body>
        <h1>Standalone Plaid Link Test</h1>
        
        <div class="info-box">
            <h3>Instructions</h3>
            <p>This is a completely standalone HTML file that tests the Plaid Link integration directly. It doesn't require any backend server.</p>
            <p><strong>When using sandbox mode, use these credentials:</strong></p>
            <ul>
                <li>Username: <code>user_good</code></li>
                <li>Password: <code>pass_good</code></li>
            </ul>
        </div>
        
        <div class="container">
            <h2>Test Plaid Link</h2>
            <p>Client ID being used: <code>""" + PLAID_CLIENT_ID + """</code></p>
            
            <div>
                <button id="linkButton">Connect with Plaid</button>
                <button id="clearLog">Clear Log</button>
            </div>
            
            <div id="log"></div>
        </div>
        
        <!-- Use the latest Plaid Link library -->
        <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
        <script>
            // Logging utilities
            const log = document.getElementById('log');
            
            function logMessage(msg, isError = false) {
                const time = new Date().toLocaleTimeString();
                const className = isError ? 'error' : '';
                log.innerHTML += `<div class="${className}">[${time}] ${msg}</div>`;
                log.scrollTop = log.scrollHeight;
                console.log(`[${time}] ${msg}`);
            }
            
            function logObject(label, obj) {
                const time = new Date().toLocaleTimeString();
                log.innerHTML += `<div>[${time}] ${label}:</div>`;
                log.innerHTML += `<pre>${JSON.stringify(obj, null, 2)}</pre>`;
                log.scrollTop = log.scrollHeight;
                console.log(`[${time}] ${label}:`, obj);
            }
            
            // Initialize on page load
            document.addEventListener('DOMContentLoaded', function() {
                logMessage('Page loaded');
                try {
                    logMessage('Browser: ' + navigator.userAgent);
                    logMessage('Protocol: ' + window.location.protocol);
                    logMessage('Host: ' + window.location.host);
                } catch (e) {
                    logMessage('Error getting browser info: ' + e.message, true);
                }
            });
            
            // Connect button handler
            document.getElementById('linkButton').addEventListener('click', function() {
                logMessage('Connect button clicked');
                
                try {
                    const linkHandler = Plaid.create({
                        // Core configuration
                        env: 'sandbox',
                        clientName: 'ConsulWealth Test App',
                        key: '""" + PLAID_CLIENT_ID + """',
                        product: ['auth', 'transactions'],
                        language: 'en',
                        countryCodes: ['US'],
                        
                        // Event handlers
                        onLoad: function() {
                            logMessage('Plaid Link loaded successfully');
                        },
                        onSuccess: function(public_token, metadata) {
                            logMessage('SUCCESS! Public token received');
                            logObject('Public token', public_token);
                            logObject('Metadata', metadata);
                            
                            // If you want to send the token to your server:
                            logMessage('You would now send this token to your server with:');
                            logMessage(`fetch('/users/api/plaid/exchange-public-token/', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                                },
                                body: JSON.stringify({ public_token: public_token })
                            })`);
                        },
                        onExit: function(err, metadata) {
                            if (err) {
                                logMessage('Error encountered during Link flow', true);
                                logObject('Error', err);
                            }
                            logMessage('User exited Plaid Link');
                            if (metadata) {
                                logObject('Exit metadata', metadata);
                                
                                if (metadata.status === 'requires_credentials') {
                                    logMessage('The Plaid Link dialog closed before credentials were entered', true);
                                    logMessage('This might be because:', true);
                                    logMessage('1. The client ID is not valid for this environment', true);
                                    logMessage('2. Domain restrictions are enabled in Plaid Dashboard', true);
                                    logMessage('3. Network issues are preventing communication with Plaid', true);
                                }
                            }
                        },
                        onEvent: function(eventName, metadata) {
                            logMessage('Event: ' + eventName);
                            if (metadata && Object.keys(metadata).length > 0) {
                                logObject('Event metadata', metadata);
                            }
                        },
                    });
                    
                    // Open Plaid Link
                    linkHandler.open();
                    logMessage('Plaid Link dialog opened');
                    
                } catch (error) {
                    logMessage('Error initializing Plaid Link: ' + error.message, true);
                    logMessage('Stack trace: ' + error.stack, true);
                    console.error('Plaid initialization error:', error);
                }
            });
            
            // Clear log button handler
            document.getElementById('clearLog').addEventListener('click', function() {
                log.innerHTML = '';
                logMessage('Log cleared');
            });
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html) 