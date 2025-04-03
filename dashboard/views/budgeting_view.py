"""
Views for budgeting functionality.
"""
from django.shortcuts import render
import logging
from supabase_integration.decorators import login_required
from supabase_integration.adapter import SupabaseAdapter
from datetime import datetime, timedelta
import json
import calendar
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

@login_required
def budgeting_view(request):
    """Budgeting view with transaction data processing"""
    # Get Supabase user ID directly from request.user
    supabase_id = request.user.id
    
    # Initialize Supabase adapter
    adapter = SupabaseAdapter()
    
    # Get date range for transactions (default to current month)
    now = datetime.now()
    
    # Check for month parameter in the request
    month_param = request.GET.get('month', 'current')
    
    # Calculate the appropriate date range based on the month parameter
    if month_param == 'current':
        # Use current month
        end_date = now.date()
        start_date = end_date.replace(day=1)  # First day of current month
    else:
        try:
            # Convert month_param to integer (should be negative for past months)
            months_offset = int(month_param)
            
            # Adjust date range based on the offset
            if months_offset < 0:
                # For past months, calculate the date range
                target_date = now + relativedelta(months=months_offset)
                end_date = target_date.date()
                # Get the last day of the month
                last_day = calendar.monthrange(end_date.year, end_date.month)[1]
                end_date = end_date.replace(day=last_day)
                start_date = end_date.replace(day=1)  # First day of the month
            else:
                # Default to current month for invalid values
                end_date = now.date()
                start_date = end_date.replace(day=1)
                
            logger.info(f"Using date range: {start_date} to {end_date} for month_param: {month_param}")
        except ValueError:
            # Handle invalid month parameter
            logger.warning(f"Invalid month parameter: {month_param}, using current month")
            end_date = now.date()
            start_date = end_date.replace(day=1)
    
    # Calculate date for the monthly view
    current_month_name = datetime(start_date.year, start_date.month, 1).strftime('%B %Y')
    
    # Get accounts to add account names to transactions
    accounts = adapter.get_accounts(supabase_id)
    account_map = {account['id']: account for account in accounts}
    
    # Identify investment accounts (for filtering)
    investment_account_ids = []
    for account in accounts:
        if account.get('is_investment') or account.get('is_investment_account') or account.get('type') == 'investment':
            if 'id' in account:
                investment_account_ids.append(account['id'])
    
    # Initialize context with default values
    context = {
        'page_title': 'Budgeting',
        'current_month': current_month_name,
        'monthly_income': 0,
        'monthly_spending': 0,
        'net_savings': 0,
        'savings_rate': 0,
        'spending_by_category': {},
        'has_transactions': False,
        'selected_month': month_param,  # Pass the selected month back to template
    }
    
    try:
        # Get transactions from Supabase for the selected month
        if supabase_id:
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            transactions = adapter.get_transactions(
                supabase_id, 
                start_date=start_date_str, 
                end_date=end_date_str
            )
            
            # If no transactions found for the selected month and it's the current month,
            # try to find the most recent month with transactions
            if not transactions and month_param == 'current':
                logger.info("No transactions found for current month, fetching all available transactions")
                transactions = adapter.get_transactions(supabase_id)
                
                # If we have transactions, find the most recent month with data
                if transactions:
                    # Sort transactions by date (newest first)
                    transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
                    
                    # Get the most recent transaction date
                    most_recent_date = datetime.strptime(transactions[0]['date'], '%Y-%m-%d').date()
                    
                    # Update date range to that month
                    end_date = most_recent_date
                    start_date = end_date.replace(day=1)
                    
                    # Update month name
                    current_month_name = end_date.strftime('%B %Y')
                    context['current_month'] = current_month_name
                    
                    # Re-fetch transactions for that month only
                    start_date_str = start_date.isoformat()
                    end_date_str = end_date.isoformat()
                    
                    transactions = adapter.get_transactions(
                        supabase_id, 
                        start_date=start_date_str, 
                        end_date=end_date_str
                    )
                    
                    logger.info(f"Found transactions for {current_month_name}")
            
            # Filter out investment transactions
            if investment_account_ids:
                transactions = [t for t in transactions if t.get('account_id') not in investment_account_ids]
            
            # Add account names to transactions
            for transaction in transactions:
                account_id = transaction.get('account_id')
                if account_id in account_map:
                    transaction['account_name'] = account_map[account_id].get('name', 'Unknown Account')
                else:
                    transaction['account_name'] = 'Unknown Account'
            
            if transactions:
                logger.info(f"Successfully retrieved {len(transactions)} transactions for {current_month_name} budgeting")
                
                # Calculate monthly income (negative amounts are deposits in Plaid format)
                monthly_income = sum(abs(float(t.get('amount', 0))) for t in transactions if float(t.get('amount', 0)) < 0)
                
                # Calculate total spending (positive amounts are expenses)
                monthly_spending = sum(float(t.get('amount', 0)) for t in transactions if float(t.get('amount', 0)) > 0)
                
                # Calculate net savings
                net_savings = monthly_income - monthly_spending
                
                # Compute spending by category
                spending_by_category = {}
                for transaction in transactions:
                    category = transaction.get('category', 'Uncategorized')
                    # Clean up category names
                    if not category or category.lower() == 'null' or category.lower() == 'none':
                        category = 'Uncategorized'
                    
                    amount = float(transaction.get('amount', 0))
                    
                    # Filter out transfers from regular expense calculations 
                    is_transfer = (
                        category.lower() == 'transfer' or 
                        'transfer' in category.lower() or 
                        'venmo' in transaction.get('name', '').lower() or
                        'zelle' in transaction.get('name', '').lower()
                    )
                    
                    # Only include expenses (positive amount in Plaid format)
                    if amount > 0:
                        # Track transfers separately
                        if is_transfer:
                            category = 'Transfer'
                            
                        if category in spending_by_category:
                            spending_by_category[category] += amount
                        else:
                            spending_by_category[category] = amount
                
                # Re-calculate monthly spending WITHOUT transfer amounts for better financial insight
                transfer_amount = spending_by_category.get('Transfer', 0)
                actual_spending = monthly_spending - transfer_amount
                
                # Recalculate savings rate based on actual spending (excluding transfers)
                if monthly_income > 0:
                    savings_rate = int(((monthly_income - actual_spending) / monthly_income) * 100)
                
                # Limit to top 10 categories if there are too many
                if len(spending_by_category) > 10:
                    sorted_categories = sorted(spending_by_category.items(), key=lambda x: x[1], reverse=True)
                    top_categories = dict(sorted_categories[:9])  # Take top 9
                    others_sum = sum(value for _, value in sorted_categories[9:])
                    top_categories['Other'] = others_sum
                    spending_by_category = top_categories
                
                # Convert spending by category to chart format
                category_labels = list(spending_by_category.keys())
                category_data = list(spending_by_category.values())
                
                # Calculate weekly spending trends (improved algorithm)
                weekly_spending = {}
                
                # Get weeks of the selected month
                current_month_start = start_date
                current_month_end = end_date
                
                # Create week buckets
                week_number = 1
                while True:
                    week_start = current_month_start + timedelta(days=(week_number-1)*7)
                    if week_start.month != current_month_start.month:
                        break
                    
                    week_end = min(week_start + timedelta(days=6), current_month_end)
                    if week_end.month != current_month_start.month:
                        week_end = current_month_start.replace(day=calendar.monthrange(
                            current_month_start.year, current_month_start.month)[1])
                    
                    week_label = f"Week {week_number}"
                    weekly_spending[week_label] = 0
                    week_number += 1
                    
                    if week_end >= current_month_end:
                        break
                
                # If no weeks were created (rare edge case), create at least one
                if not weekly_spending:
                    weekly_spending["Week 1"] = 0
                
                # Assign transactions to weeks
                for transaction in transactions:
                    if 'date' not in transaction:
                        continue
                    
                    tx_date = datetime.strptime(transaction['date'], '%Y-%m-%d').date()
                    amount = float(transaction.get('amount', 0))
                    
                    # Only include expenses
                    if amount <= 0:
                        continue
                    
                    # Find which week this transaction belongs to
                    days_from_start = (tx_date - current_month_start).days
                    week_index = days_from_start // 7 + 1
                    week_label = f"Week {week_index}"
                    
                    # Some weeks might not exist in our buckets if the month is incomplete
                    if week_label in weekly_spending:
                        weekly_spending[week_label] += amount
                
                # Update context with calculated values
                context.update({
                    'monthly_income': monthly_income,
                    'monthly_spending': monthly_spending,
                    'net_savings': net_savings,
                    'savings_rate': savings_rate,
                    'spending_by_category': spending_by_category,
                    'category_labels': json.dumps(category_labels),
                    'category_data': json.dumps(category_data),
                    'weekly_labels': json.dumps(list(weekly_spending.keys())),
                    'weekly_data': json.dumps(list(weekly_spending.values())),
                    'has_transactions': True,
                    'transfer_amount': transfer_amount,
                    'actual_spending': actual_spending
                })
                
                # Calculate trend data for past 6 months to enhance projection chart
                past_months_data = []
                
                # Use the selected month as the reference point
                reference_date = datetime(end_date.year, end_date.month, 1)
                
                for i in range(6):
                    # Calculate months relative to the selected month
                    month_date = reference_date - relativedelta(months=i)
                    month_end = month_date.replace(day=calendar.monthrange(month_date.year, month_date.month)[1])
                    month_start = month_date.replace(day=1)
                    
                    # Format dates for Supabase
                    month_start_str = month_start.isoformat()
                    month_end_str = month_end.isoformat()
                    
                    # Get transactions for this month
                    month_transactions = adapter.get_transactions(
                        supabase_id, 
                        start_date=month_start_str, 
                        end_date=month_end_str
                    )
                    
                    # Filter out investment transactions
                    if investment_account_ids:
                        month_transactions = [t for t in month_transactions if t.get('account_id') not in investment_account_ids]
                    
                    # Calculate net for this month
                    month_income = sum(abs(float(t.get('amount', 0))) for t in month_transactions if float(t.get('amount', 0)) < 0)
                    month_expenses = sum(float(t.get('amount', 0)) for t in month_transactions if float(t.get('amount', 0)) > 0)
                    month_net = month_income - month_expenses
                    
                    month_name = month_end.strftime('%b %Y')
                    past_months_data.append({
                        'month': month_name,
                        'net': month_net
                    })
                
                # Reverse to get chronological order
                past_months_data.reverse()
                
                # Add to context
                context['past_months_data'] = json.dumps(past_months_data)
            else:
                logger.warning("No transactions found for budgeting view")
        else:
            logger.warning("No Supabase ID available for user in budgeting view")
    except Exception as e:
        logger.error(f"Error in budgeting view: {str(e)}")
        logger.exception("Full exception details:")
    
    return render(request, 'dashboard/budgeting.html', context) 