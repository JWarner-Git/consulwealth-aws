"""
Views for transaction display with different filtering options.
"""
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from supabase_integration.adapter import SupabaseAdapter
from supabase_integration.decorators import login_required
import logging
from datetime import datetime, timedelta
import calendar
import json

logger = logging.getLogger(__name__)

@login_required
def regular_transactions_view(request):
    """Display only regular transactions, excluding investment transactions"""
    # Get Supabase user ID directly from request.user
    supabase_id = request.user.id
    
    # Initialize Supabase adapter
    adapter = SupabaseAdapter()
    
    # Get date range for transactions (default to last 90 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    # Get filter parameters from request
    date_filter = request.GET.get('date_filter', 'last_90_days')
    category = request.GET.get('category', '')
    account_id = request.GET.get('account', '')
    search = request.GET.get('search', '')
    
    # Adjust date range based on filter
    if date_filter == 'last_7_days':
        start_date = end_date - timedelta(days=7)
    elif date_filter == 'last_30_days':
        start_date = end_date - timedelta(days=30)
    elif date_filter == 'current_month':
        start_date = end_date.replace(day=1)
    elif date_filter == 'last_month':
        last_month = end_date.month - 1 if end_date.month > 1 else 12
        last_month_year = end_date.year if end_date.month > 1 else end_date.year - 1
        last_month_days = calendar.monthrange(last_month_year, last_month)[1]
        start_date = datetime(last_month_year, last_month, 1).date()
        end_date = datetime(last_month_year, last_month, last_month_days).date()
    
    # Format dates for Supabase
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    # Get all transactions from Supabase
    transactions = adapter.get_transactions(
        supabase_id, 
        start_date=start_date_str, 
        end_date=end_date_str,
        account_id=account_id if account_id else None
    )
    
    # Get accounts to add account names to transactions
    accounts = adapter.get_accounts(supabase_id)
    account_map = {account['id']: account for account in accounts}
    
    # Filter out investment accounts
    investment_account_ids = []
    regular_accounts = []
    
    for account in accounts:
        if account.get('is_investment') or account.get('is_investment_account') or account.get('type') == 'investment':
            if 'id' in account:
                investment_account_ids.append(account['id'])
        else:
            regular_accounts.append(account)
    
    # Add account names to transactions and filter out investment transactions
    regular_transactions = []
    for transaction in transactions:
        account_id = transaction.get('account_id')
        is_investment_transaction = account_id in investment_account_ids
        
        # Add account name
        if account_id in account_map:
            transaction['account_name'] = account_map[account_id].get('name', 'Unknown Account')
        else:
            transaction['account_name'] = 'Unknown Account'
            
        # Only include non-investment transactions
        if not is_investment_transaction:
            # Apply additional filtering (category and search)
            if category and category.lower() not in (transaction.get('category') or '').lower():
                continue
                
            if search and not (search.lower() in (transaction.get('merchant_name') or '').lower() or 
                              search.lower() in (transaction.get('name') or '').lower() or
                              search.lower() in (transaction.get('category') or '').lower()):
                continue
                
            regular_transactions.append(transaction)
    
    # Calculate account cash flow
    account_cash_flow = {}
    for account in regular_accounts:
        account_id = account.get('id')
        if account_id:
            account_cash_flow[account_id] = {
                'name': account.get('name', 'Unknown Account'),
                'inflows': 0.0,
                'outflows': 0.0,
                'net': 0.0
            }
    
    # Calculate spending by category and account cash flow
    spending_by_category = {}
    total_inflows = 0.0
    total_outflows = 0.0
    
    # Prepare monthly data
    last_5_months = []
    monthly_income = {}
    monthly_expenses = {}
    
    # Get the last 5 months
    for i in range(5):
        month_date = end_date - timedelta(days=30 * i)
        month_name = month_date.strftime('%B')
        last_5_months.append(month_name)
        monthly_income[month_name] = 0.0
        monthly_expenses[month_name] = 0.0
    
    # Process transactions
    for transaction in regular_transactions:
        category = transaction.get('category', 'Uncategorized')
        amount = float(transaction.get('amount', 0))
        account_id = transaction.get('account_id')
        transaction_date = datetime.strptime(transaction.get('date', end_date.isoformat()), '%Y-%m-%d').date()
        transaction_month = transaction_date.strftime('%B')
        
        # Check if this is a transfer transaction
        is_transfer = (
            category.lower() == 'transfer' or 
            'transfer' in category.lower() or 
            'venmo' in (transaction.get('merchant_name', '') or transaction.get('name', '')).lower() or
            'zelle' in (transaction.get('merchant_name', '') or transaction.get('name', '')).lower()
        )
        
        # Update account cash flow
        if account_id in account_cash_flow:
            if amount < 0:  # Income (negative in Plaid format)
                account_cash_flow[account_id]['inflows'] += abs(amount)
                total_inflows += abs(amount)
                
                # Update monthly income if in the last 5 months
                if transaction_month in monthly_income:
                    monthly_income[transaction_month] += abs(amount)
            else:  # Expense
                account_cash_flow[account_id]['outflows'] += amount
                total_outflows += amount
                
                # Update monthly expenses if in the last 5 months
                if transaction_month in monthly_expenses:
                    monthly_expenses[transaction_month] += amount
                
                # Track spending by category (exclude transfers)
                if not is_transfer:
                    if category in spending_by_category:
                        spending_by_category[category] += amount
                    else:
                        spending_by_category[category] = amount
    
    # Calculate net cash flow for each account
    for account_id, data in account_cash_flow.items():
        data['net'] = data['inflows'] - data['outflows']
        
    # Convert account cash flow to list for template
    accounts_with_cash_flow = []
    for account_id, data in account_cash_flow.items():
        accounts_with_cash_flow.append({
            'id': account_id,
            'name': data['name'],
            'inflows': round(data['inflows'], 2),
            'outflows': round(data['outflows'], 2),
            'net': round(data['net'], 2)
        })
    
    # Calculate total net
    total_net = total_inflows - total_outflows
    
    # Sort by most recent first
    regular_transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Paginate results
    page_number = request.GET.get('page', 1)
    paginator = Paginator(regular_transactions, 10)  # Show 10 transactions per page
    
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    # Generate dummy upcoming payments (for demonstration)
    upcoming_payments = [
        {'type': 'Bill', 'name': 'Internet Service', 'amount': 79.99, 'date': 'May 15'},
        {'type': 'Subscription', 'name': 'Netflix', 'amount': 14.99, 'date': 'May 18'},
        {'type': 'Bill', 'name': 'Electricity', 'amount': 120.00, 'date': 'May 22'}
    ]
    
    # Prepare JSON data for charts
    category_data_json = json.dumps({k: round(v, 2) for k, v in spending_by_category.items()})
    monthly_income_json = json.dumps({month: round(monthly_income.get(month, 0), 2) for month in last_5_months})
    monthly_expenses_json = json.dumps({month: round(monthly_expenses.get(month, 0), 2) for month in last_5_months})
    last_5_months_json = json.dumps(last_5_months)
    
    context = {
        'page_title': 'Transactions',
        'transactions': page_obj,
        'accounts': regular_accounts,
        'total_inflows': round(total_inflows, 2),
        'total_outflows': round(total_outflows, 2),
        'total_net': round(total_net, 2),
        'spending_by_category': spending_by_category,
        'category_data_json': category_data_json,
        'monthly_income_json': monthly_income_json, 
        'monthly_expenses_json': monthly_expenses_json,
        'last_5_months_json': last_5_months_json,
        'investment_account_ids': investment_account_ids,
        'has_plaid_data': bool(accounts),
        'total_transactions': len(regular_transactions),
        'account_cash_flow': accounts_with_cash_flow,
        'upcoming_payments': upcoming_payments
    }
    
    return render(request, 'dashboard/transactions.html', context)

@login_required
def all_transactions_view(request):
    """Display ALL transactions including investment transactions"""
    # Get Supabase user ID directly from request.user
    supabase_id = request.user.id
    
    # Initialize Supabase adapter
    adapter = SupabaseAdapter()
    
    # Get date range for transactions (default to last 90 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    # Get filter parameters from request
    date_filter = request.GET.get('date_filter', 'last_90_days')
    category = request.GET.get('category', '')
    account_id = request.GET.get('account', '')
    search = request.GET.get('search', '')
    
    # Adjust date range based on filter
    if date_filter == 'last_7_days':
        start_date = end_date - timedelta(days=7)
    elif date_filter == 'last_30_days':
        start_date = end_date - timedelta(days=30)
    elif date_filter == 'current_month':
        start_date = end_date.replace(day=1)
    elif date_filter == 'last_month':
        last_month = end_date.month - 1 if end_date.month > 1 else 12
        last_month_year = end_date.year if end_date.month > 1 else end_date.year - 1
        last_month_days = calendar.monthrange(last_month_year, last_month)[1]
        start_date = datetime(last_month_year, last_month, 1).date()
        end_date = datetime(last_month_year, last_month, last_month_days).date()
    
    # Format dates for Supabase
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    # Get transactions from Supabase without filtering out investment transactions
    transactions = adapter.get_transactions(
        supabase_id, 
        start_date=start_date_str, 
        end_date=end_date_str,
        account_id=account_id if account_id else None
    )
    
    # Apply additional filtering in Python (category and search)
    if category:
        transactions = [t for t in transactions if category.lower() in (t.get('category') or '').lower()]
    
    if search:
        transactions = [t for t in transactions if 
            search.lower() in (t.get('merchant_name') or '').lower() or 
            search.lower() in (t.get('name') or '').lower() or
            search.lower() in (t.get('category') or '').lower()]
    
    # Get accounts to add account names to transactions
    accounts = adapter.get_accounts(supabase_id)
    account_map = {account['id']: account for account in accounts}
    
    # Identify investment accounts (for display purposes, not filtering)
    investment_account_ids = []
    for account in accounts:
        if account.get('is_investment') or account.get('is_investment_account') or account.get('type') == 'investment':
            if 'id' in account:
                investment_account_ids.append(account['id'])
    
    # Add account names to transactions
    for transaction in transactions:
        account_id = transaction.get('account_id')
        if account_id in account_map:
            transaction['account_name'] = account_map[account_id].get('name', 'Unknown Account')
            transaction['account_type'] = account_map[account_id].get('type', 'unknown')
            transaction['is_investment'] = account_id in investment_account_ids
        else:
            transaction['account_name'] = 'Unknown Account'
            transaction['account_type'] = 'unknown'
            transaction['is_investment'] = False
    
    # Calculate spending by category (for all transactions)
    spending_by_category = {}
    income_by_category = {}
    
    for transaction in transactions:
        category = transaction.get('category', 'Uncategorized')
        amount = float(transaction.get('amount', 0))
        
        # Check if this is a transfer transaction
        is_transfer = (
            category.lower() == 'transfer' or 
            'transfer' in category.lower() or 
            'venmo' in (transaction.get('merchant_name', '') or transaction.get('name', '')).lower() or
            'zelle' in (transaction.get('merchant_name', '') or transaction.get('name', '')).lower()
        )
        
        # Negative amounts are income in Plaid format
        if amount < 0:
            # Store as positive for display
            if category in income_by_category:
                income_by_category[category] += abs(amount)
            else:
                income_by_category[category] = abs(amount)
        else:
            # Positive amounts are expenses (exclude transfers)
            if not is_transfer:
                if category in spending_by_category:
                    spending_by_category[category] += amount
                else:
                    spending_by_category[category] = amount
    
    # Prepare data for charts
    spending_categories = list(spending_by_category.keys())
    spending_amounts = [spending_by_category[cat] for cat in spending_categories]
    
    income_categories = list(income_by_category.keys())
    income_amounts = [income_by_category[cat] for cat in income_categories]
    
    # Calculate totals
    total_spending = sum(spending_by_category.values())
    total_income = sum(income_by_category.values())
    net_cashflow = total_income - total_spending
    
    # Save the total count before filtering
    total_transactions_count = len(transactions)
    
    # Paginate results
    page_number = request.GET.get('page', 1)
    paginator = Paginator(transactions, 10)  # Show 10 transactions per page (reduced from 25)
    
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'page_title': 'All Transactions',
        'transactions': page_obj,
        'accounts': accounts,
        'investment_account_ids': investment_account_ids,
        'date_filter': date_filter,
        'selected_account': account_id,
        'spending_by_category': spending_by_category,
        'income_by_category': income_by_category,
        'spending_categories': spending_categories,
        'income_categories': income_categories,
        'total_spending': total_spending,
        'total_income': total_income,
        'net_cashflow': net_cashflow,
        'has_plaid_data': bool(accounts),
        'total_transactions': total_transactions_count,
        'show_all_transactions': True,  # Flag to indicate this view shows all transactions
    }
    
    return render(request, 'dashboard/all_transactions.html', context) 