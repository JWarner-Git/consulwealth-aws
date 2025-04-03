"""
Debug view to examine transaction retrieval.
"""
from django.http import JsonResponse
from supabase_integration.adapter import SupabaseAdapter
from supabase_integration.decorators import login_required
from supabase_integration.services import PlaidService
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@login_required
def debug_transactions(request):
    """Debug view to trace transaction retrieval logic"""
    # Get user ID
    user_id = request.user.id
    
    # Initialize adapter
    adapter = SupabaseAdapter()
    
    # Get accounts
    accounts = adapter.get_accounts(user_id)
    account_ids = [account.get('account_id') for account in accounts if account.get('account_id')]
    
    # Get raw transactions without date filtering
    try:
        # Call the implementation directly to see what's happening
        transactions = adapter.get_transactions(user_id, None, None)
    
        # Count negative and positive amounts
        negative_amounts = []
        positive_amounts = []
        for t in transactions:
            try:
                amount = float(t.get('amount', 0))
                if amount < 0:
                    negative_amounts.append({
                        'id': t.get('id'),
                        'date': t.get('date'),
                        'name': t.get('name') or t.get('merchant_name'),
                        'amount': amount,
                        'account_id': t.get('account_id')
                    })
                else:
                    positive_amounts.append({
                        'id': t.get('id'),
                        'date': t.get('date'),
                        'name': t.get('name') or t.get('merchant_name'),
                        'amount': amount,
                        'account_id': t.get('account_id')
                    })
            except (ValueError, TypeError):
                pass
        
        # Prepare debug info
        debug_info = {
            "user_id": user_id,
            "account_count": len(accounts),
            "account_ids": account_ids[:10] if account_ids else [],  # Show first 10
            "transaction_count": len(transactions),
            "income_transactions_count": len(negative_amounts),
            "expense_transactions_count": len(positive_amounts),
            "sample_income_transactions": negative_amounts[:5] if negative_amounts else [],  # Show first 5 income transactions
            "sample_expense_transactions": positive_amounts[:5] if positive_amounts else [],  # Show first 5 expense transactions
        }
        
        return JsonResponse(debug_info)
    except Exception as e:
        logger.exception("Error in debug view")
        return JsonResponse({"error": str(e)})

@login_required
def debug_transaction_display(request):
    """Debug view to show why transactions might not be displaying correctly in the template"""
    # Get user ID
    user_id = request.user.id
    
    # Initialize adapter
    adapter = SupabaseAdapter()
    
    # Get date range for transactions (default to last 90 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    # Get transactions using the same approach as the transactions_view
    transactions = adapter.get_transactions(
        user_id, 
        start_date=start_date_str, 
        end_date=end_date_str
    )
    
    # Get accounts
    accounts = adapter.get_accounts(user_id)
    account_map = {account['id']: account for account in accounts}
    
    # Identify investment accounts
    investment_account_ids = []
    for account in accounts:
        if account.get('is_investment') or account.get('is_investment_account') or account.get('type') == 'investment':
            if 'id' in account:
                investment_account_ids.append(account['id'])
            if 'account_id' in account:
                investment_account_ids.append(account['account_id'])
    
    # Track how transactions would be filtered in the template
    filtered_transactions = []
    removed_transactions = []
    
    for transaction in transactions:
        account_id = transaction.get('account_id')
        account_in_investment = account_id in investment_account_ids
        amount = float(transaction.get('amount', 0)) if transaction.get('amount') is not None else 0
        
        transaction_info = {
            'id': transaction.get('id'),
            'date': transaction.get('date'),
            'name': transaction.get('name') or transaction.get('merchant_name'),
            'amount': amount,
            'account_id': account_id,
            'account_in_investment': account_in_investment,
            'is_income': amount < 0,
        }
        
        if not account_in_investment:
            filtered_transactions.append(transaction_info)
        else:
            removed_transactions.append(transaction_info)
    
    # Prepare debug info
    debug_info = {
        "user_id": user_id,
        "account_count": len(accounts),
        "investment_account_ids": investment_account_ids,
        "total_transaction_count": len(transactions),
        "displayed_transaction_count": len(filtered_transactions),
        "filtered_out_transaction_count": len(removed_transactions),
        "income_transactions_displayed": len([t for t in filtered_transactions if t['is_income']]),
        "income_transactions_filtered_out": len([t for t in removed_transactions if t['is_income']]),
        "sample_displayed_transactions": filtered_transactions[:5],
        "sample_filtered_out_transactions": removed_transactions[:5],
    }
    
    return JsonResponse(debug_info)

@login_required
def transaction_debug(request):
    """Debug view to check why transactions aren't displaying properly"""
    # Get user ID directly from request.user
    user_id = request.user.id
    
    # Initialize adapter
    adapter = SupabaseAdapter()
    
    # Get all accounts
    accounts = adapter.get_accounts(user_id)
    account_ids = [a.get('id') for a in accounts]
    
    # Get all transactions without filtering
    all_txs = adapter.get_transactions(user_id, None, None)
    
    # Check which transactions would be filtered as investment transactions
    investment_accounts = [a for a in accounts if a.get('is_investment') or 
                         a.get('is_investment_account') or 
                         a.get('type') == 'investment']
    investment_account_ids = [a.get('id') for a in investment_accounts]
    
    # Find transactions that would be filtered out
    filtered_txs = [tx for tx in all_txs if tx.get('account_id') not in investment_account_ids]
    investment_txs = [tx for tx in all_txs if tx.get('account_id') in investment_account_ids]
    
    # Check for income transactions (negative amounts in Plaid format)
    income_txs = [tx for tx in all_txs if float(tx.get('amount', 0)) < 0]
    expense_txs = [tx for tx in all_txs if float(tx.get('amount', 0)) >= 0]
    
    # Check for income transactions among filtered transactions
    filtered_income_txs = [tx for tx in filtered_txs if float(tx.get('amount', 0)) < 0]
    
    # Prepare debug info
    debug_info = {
        'total_transactions': len(all_txs),
        'non_investment_transactions': len(filtered_txs),
        'investment_transactions': len(investment_txs),
        'income_transactions': len(income_txs),
        'expense_transactions': len(expense_txs),
        'non_investment_income_transactions': len(filtered_income_txs),
        'account_count': len(accounts),
        'investment_account_count': len(investment_accounts),
        'account_ids': account_ids,
        'investment_account_ids': investment_account_ids,
        'sample_transactions': [tx for tx in all_txs[:5]],
        'sample_income_transactions': [tx for tx in income_txs[:5]],
        'sample_investment_transactions': [tx for tx in investment_txs[:5]],
    }
    
    return JsonResponse(debug_info)

@login_required
def manual_transaction_sync(request):
    """Debug view to manually trigger a transaction sync and see the results"""
    # Get user ID
    user_id = request.user.id
    
    # Initialize adapter and service
    adapter = SupabaseAdapter()
    plaid_service = PlaidService()
    
    # Get proper date range (last 90 days from today)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    # Show date range in readable format for debugging
    start_date_formatted = start_date.strftime('%Y-%m-%d')
    end_date_formatted = end_date.strftime('%Y-%m-%d')
    
    # Try to manually trigger transaction sync
    response_data = {
        "user_id": user_id,
        "sync_attempted": True,
        "start_date": start_date_formatted,  # Use formatted date for display
        "end_date": end_date_formatted,      # Use formatted date for display
        "start_date_raw": start_date.isoformat(),  # Keep the ISO format for debugging
        "end_date_raw": end_date.isoformat(),      # Keep the ISO format for debugging
        "plaid_items": [],
        "success": False,
        "error": None,
    }
    
    try:
        # Get Plaid items for the user
        plaid_items = adapter.get_plaid_items(user_id)
        response_data["plaid_items_count"] = len(plaid_items)
        
        if not plaid_items:
            response_data["error"] = "No Plaid items found for this user"
            return JsonResponse(response_data)
        
        # For each Plaid item, try to sync transactions
        for item in plaid_items:
            item_info = {
                "item_id": item.get("id"),
                "institution_id": item.get("institution_id"),
                "sync_attempted": True,
                "sync_success": False,
                "transactions_before": 0,
                "transactions_after": 0,
                "error": None
            }
            
            try:
                # Count transactions before sync
                transactions_before = len(adapter.get_transactions(user_id))
                item_info["transactions_before"] = transactions_before
                
                # Attempt to sync transactions for this item (use actual past dates)
                result = plaid_service.sync_transactions(
                    request.user,
                    start_date.isoformat(),  # Use actual past date
                    end_date.isoformat()     # Use today as end date
                )
                
                # Count transactions after sync
                transactions_after = len(adapter.get_transactions(user_id))
                item_info["transactions_after"] = transactions_after
                item_info["sync_success"] = True
                item_info["new_transactions_count"] = transactions_after - transactions_before
                
            except Exception as e:
                logger.exception(f"Error syncing transactions for item {item.get('id')}")
                item_info["error"] = str(e)
            
            response_data["plaid_items"].append(item_info)
        
        response_data["success"] = any(item.get("sync_success", False) for item in response_data["plaid_items"])
        
        # Check if any transactions were added
        response_data["total_transactions_after_sync"] = len(adapter.get_transactions(user_id))
        
    except Exception as e:
        logger.exception("Error in manual transaction sync")
        response_data["error"] = str(e)
    
    return JsonResponse(response_data)

@login_required
def fixed_date_transaction_sync(request):
    """Debug view to sync transactions using a fixed historical date range (2023)"""
    # Get user ID
    user_id = request.user.id
    
    # Initialize adapter and service
    adapter = SupabaseAdapter()
    plaid_service = PlaidService()
    
    # Use a fixed date range in the past (2023)
    start_date = datetime(2023, 1, 1).date()
    end_date = datetime(2023, 12, 31).date()
    
    # Show date range in readable format for debugging
    start_date_formatted = start_date.strftime('%Y-%m-%d')
    end_date_formatted = end_date.strftime('%Y-%m-%d')
    
    # Try to manually trigger transaction sync
    response_data = {
        "user_id": user_id,
        "sync_attempted": True,
        "start_date": start_date_formatted,
        "end_date": end_date_formatted,
        "system_time": datetime.now().strftime('%Y-%m-%d'),
        "plaid_items": [],
        "success": False,
        "error": None,
    }
    
    try:
        # Get Plaid items for the user
        plaid_items = adapter.get_plaid_items(user_id)
        response_data["plaid_items_count"] = len(plaid_items)
        
        if not plaid_items:
            response_data["error"] = "No Plaid items found for this user"
            return JsonResponse(response_data)
        
        # For each Plaid item, try to sync transactions
        for item in plaid_items:
            item_info = {
                "item_id": item.get("id"),
                "institution_id": item.get("institution_id"),
                "sync_attempted": True,
                "sync_success": False,
                "transactions_before": 0,
                "transactions_after": 0,
                "error": None
            }
            
            try:
                # Count transactions before sync
                transactions_before = len(adapter.get_transactions(user_id))
                item_info["transactions_before"] = transactions_before
                
                # Attempt to sync transactions for this item (use fixed past date)
                result = plaid_service.sync_transactions(
                    request.user,
                    start_date.isoformat(),
                    end_date.isoformat()
                )
                
                # Count transactions after sync
                transactions_after = len(adapter.get_transactions(user_id))
                item_info["transactions_after"] = transactions_after
                item_info["sync_success"] = True
                item_info["new_transactions_count"] = transactions_after - transactions_before
                
            except Exception as e:
                logger.exception(f"Error syncing transactions for item {item.get('id')}")
                item_info["error"] = str(e)
            
            response_data["plaid_items"].append(item_info)
        
        response_data["success"] = any(item.get("sync_success", False) for item in response_data["plaid_items"])
        
        # Check if any transactions were added
        response_data["total_transactions_after_sync"] = len(adapter.get_transactions(user_id))
        
    except Exception as e:
        logger.exception("Error in fixed date transaction sync")
        response_data["error"] = str(e)
    
    return JsonResponse(response_data) 