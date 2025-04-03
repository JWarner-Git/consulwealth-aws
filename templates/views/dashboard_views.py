"""
Dashboard views using Supabase data.
This module provides the main dashboard views for the application.
"""
from django.shortcuts import render, redirect
from supabase_integration.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timedelta, date
import calendar
import json
import logging
import random

from supabase_integration.adapter import SupabaseAdapter
from supabase_integration.services import SupabaseService
from supabase_integration.utils import is_investment_account

logger = logging.getLogger(__name__)

@login_required
def dashboard_view(request):
    """Main dashboard view using Supabase data"""
    try:
        # Get user's Supabase ID directly from request.user which now comes from Supabase
        supabase_id = request.user.id
        if not supabase_id:
            messages.error(request, "Unable to retrieve your Supabase ID. Please log in again.")
            return render(request, 'dashboard/dashboard.html', {'error': "User ID not available", 'has_plaid_data': False})
        
        adapter = SupabaseAdapter()
        
        # Fetch accounts from Supabase
        accounts = adapter.get_accounts(supabase_id)
        
        # Group accounts by type
        investment_accounts = [account for account in accounts if is_investment_account(account)]
        depository_accounts = [account for account in accounts if account.get('account_category') == 'depository']
        credit_accounts = [account for account in accounts if account.get('account_category') == 'credit']
        loan_accounts = [account for account in accounts if account.get('account_category') == 'loan']
        
        # Calculate various balances - use portfolio_value if available
        investment_account_total = sum(float(account.get('portfolio_value', 0) or float(account.get('current_balance', 0) or 0)) for account in investment_accounts)
        cash_balance = sum(float(account.get('current_balance', 0) or 0) for account in depository_accounts)
        credit_balance = sum(float(account.get('current_balance', 0) or 0) for account in credit_accounts)
        loan_balance = sum(float(account.get('current_balance', 0) or 0) for account in loan_accounts)
        
        # Calculate net worth
        net_worth = cash_balance + investment_account_total + credit_balance + loan_balance
        
        # Get transactions for budget analysis
        today = datetime.now().date()
        first_day = today.replace(day=1)
        
        # Get transactions for the current month
        transactions = adapter.get_transactions(supabase_id, first_day.isoformat(), today.isoformat())
        
        # Calculate monthly income and expenses
        monthly_income = sum(abs(float(t.get('amount', 0))) for t in transactions if float(t.get('amount', 0)) < 0)
        monthly_expenses = sum(float(t.get('amount', 0)) for t in transactions if float(t.get('amount', 0)) > 0)
        
        # Calculate savings rate
        savings_rate = 0
        if monthly_income > 0:
            savings_rate = round(((monthly_income - monthly_expenses) / monthly_income) * 100)
        
        # Get profile data for retirement calculations
        profile = adapter.get_user_profile(supabase_id)
        
        # Calculate retirement info
        current_age = 0
        if profile and 'date_of_birth' in profile and profile['date_of_birth']:
            dob = datetime.fromisoformat(profile['date_of_birth'].replace('Z', '+00:00')).date()
            current_age = (today - dob).days // 365
        
        # Calculate retirement related metrics - add safer handling of None values
        retirement_savings = sum(
            float(account.get('current_balance', 0) or 0) 
            for account in accounts 
            if account.get('account_subtype') and account.get('account_subtype', '').lower() in ['401k', 'ira', 'roth', 'brokerage']
        )
        target_savings = 2000000  # Default target - same as planning.html uses
        retirement_progress = min(100, int((retirement_savings / target_savings) * 100)) if target_savings > 0 else 0
        
        # Use the exact same calculation method as in planning.html localCalculation function
        if current_age > 0 and profile and 'retirement_age_goal' in profile:
            # Get user profile data if available
            retirement_age = int(profile.get('retirement_age_goal', 65))
            years_to_retirement = max(0, retirement_age - current_age)
            current_retirement_savings = float(profile.get('current_retirement_savings', 0) or 0)
            monthly_savings_goal = float(profile.get('monthly_savings_goal', 500) or 0)
            expected_annual_return = float(profile.get('expected_annual_return', 7) or 0) / 100
            
            # Calculate future value using same method as planning.html
            futureValue = current_retirement_savings * (1 + expected_annual_return) ** years_to_retirement
            
            # Add contributions the same way as planning.html does
            annual_savings = monthly_savings_goal * 12
            for i in range(years_to_retirement):
                futureValue += annual_savings * (1 + expected_annual_return) ** i
                
            projected_retirement_value = round(futureValue)
        else:
            # Default calculation if we don't have all the data
            projected_retirement_value = retirement_savings * 4
        
        # Get recent transactions
        recent_transactions = transactions[:5] if transactions else []
        
        # Add account names to transactions
        account_map = {account['id']: account for account in accounts}
        for transaction in recent_transactions:
            if transaction.get('account_id') in account_map:
                transaction['account_name'] = account_map[transaction['account_id']].get('name', 'Unknown Account')
            else:
                transaction['account_name'] = 'Unknown Account'
        
        # Add asset allocation data for charts
        try:
            # Fetch securities and holdings data
            securities = adapter.get_securities(supabase_id)
            holdings = adapter.get_holdings(supabase_id)
            
            # Create a dictionary mapping security IDs to securities
            security_lookup = {}
            for security in securities:
                if 'id' in security:
                    security_lookup[security['id']] = security
            
            # Group holdings by security
            security_holdings = {}
            
            for holding in holdings:
                security_id = holding.get('security_id')
                if security_id and security_id in security_lookup:
                    security = security_lookup[security_id]
                    
                    if security_id not in security_holdings:
                        security_holdings[security_id] = {
                            'security': security,
                            'total_value': 0,
                        }
                    
                    # Add to total value
                    value = float(holding.get('institution_value', 0) or 0)
                    security_holdings[security_id]['total_value'] += value
            
            # Group holdings by security type
            values_by_type = {}
            total_holdings_value = 0
            
            # Sum values by security type
            for security_id, data in security_holdings.items():
                security = data['security']
                value = data['total_value']
                
                # Determine security type
                security_type = security.get('type', '').lower() 
                
                # Use standardized categories for consistency
                if security_type in ('etf', 'exchange traded fund'):
                    security_type = 'ETF'
                elif security_type in ('mutual fund', 'fund'):
                    security_type = 'Mutual Fund'
                elif security_type in ('equity', 'stock'):
                    security_type = 'Stock'
                elif security_type in ('fixed income', 'bond'):
                    security_type = 'Bond'
                elif security_type == 'cash':
                    security_type = 'Cash'
                elif security_type == 'cryptocurrency':
                    security_type = 'Cryptocurrency'
                elif security_type == 'derivative':
                    security_type = 'Derivative'
                elif not security_type:
                    security_type = 'Other'
                else:
                    security_type = security_type.title()
                
                # Add to type totals
                if security_type not in values_by_type:
                    values_by_type[security_type] = 0
                values_by_type[security_type] += value
                total_holdings_value += value
            
            # Prepare asset allocation data for the chart
            asset_allocation_labels = []
            asset_allocation_data = []
            
            # Only include types with value
            for security_type, value in values_by_type.items():
                if value > 0:
                    asset_allocation_labels.append(security_type)
                    
                    # Calculate percentage of total holdings
                    percent = (value / total_holdings_value * 100) if total_holdings_value > 0 else 0
                    asset_allocation_data.append(round(percent, 2))
                    
            logger.info(f"Asset allocation labels: {asset_allocation_labels}")
            logger.info(f"Asset allocation data: {asset_allocation_data}")
            
            # Generate a realistic daily change value
            # In a real app, you'd compare today's value with yesterday's
            if investment_account_total > 0:
                # Random fluctuation between -1.5% and +1.8%
                random.seed(today.day)  # Use day as seed for consistent results
                change_pct = random.uniform(-1.5, 1.8)
                change_amount = investment_account_total * (change_pct / 100)
                todays_change_pct = round(change_pct, 1)
                todays_change_amount = round(change_amount, 2)
            else:
                todays_change_pct = 0.0
                todays_change_amount = 0.0
                
            # Calculate projected retirement value using compound growth formula
            projected_retirement_value = 0
            if current_age > 0 and profile and 'retirement_age_goal' in profile:
                # Use user profile data if available
                retirement_age = int(profile.get('retirement_age_goal', 65))
                years_to_retirement = max(0, retirement_age - current_age)
                current_retirement_savings = float(profile.get('current_retirement_savings', 0) or 0)
                monthly_savings_goal = float(profile.get('monthly_savings_goal', 500) or 0)
                expected_annual_return = float(profile.get('expected_annual_return', 7) or 0) / 100
                
                # Calculate future value of current savings with compound interest
                future_value = current_retirement_savings * ((1 + expected_annual_return) ** years_to_retirement)
                
                # Calculate future value of monthly contributions
                annual_contributions = monthly_savings_goal * 12
                future_contributions = 0
                for year in range(1, years_to_retirement + 1):
                    future_contributions += annual_contributions * ((1 + expected_annual_return) ** (years_to_retirement - year))
                
                projected_retirement_value = round(future_value + future_contributions)
            else:
                # Use a simple projection (4x current savings) if we don't have all the data
                projected_retirement_value = retirement_savings * 4
            
            # Prepare budget data for the budget chart
            budget_data = {
                'labels': ['Housing', 'Food', 'Transportation', 'Utilities', 'Entertainment'],
                'planned': [1500, 600, 400, 300, 200],
                'actual': [1450, 580, 390, 310, 220]
            }
            
            # Log what we're sending to the template
            logger.info(f"Asset allocation labels: {asset_allocation_labels}")
            logger.info(f"Asset allocation data: {asset_allocation_data}")
            logger.info(f"Total holdings value: {total_holdings_value}, Portfolio value: {investment_account_total}")
            
            # Generate monthly portfolio value data
            monthly_portfolio_data = []
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            # Generate data for all months of the current year
            month_labels = []
            month_values = []
            
            for month in range(1, 13):
                month_name = datetime(current_year, month, 1).strftime('%b')  # Short month name (Jan, Feb, etc.)
                month_labels.append(month_name)
                
                # For past months, use actual data (or 0 if no data available)
                # For current month, use current portfolio value
                # For future months, use null
                if month < current_month:
                    # Past month - for now, use a percentage of current value (can be replaced with actual historical data)
                    # This approach simulates some growth over time
                    month_growth_factor = 0.95 + (0.05 * month / current_month)  # Progressive growth toward current value
                    month_value = investment_account_total * month_growth_factor if investment_account_total > 0 else 0
                    month_values.append(round(month_value, 2))
                elif month == current_month:
                    # Current month - use actual portfolio value
                    month_values.append(investment_account_total)
                else:
                    # Future month - use null (chart will show a gap)
                    month_values.append(None)
            
            # Historical portfolio data for chart
            historical_data = {
                'labels': month_labels,
                'values': month_values
            }
            
        except Exception as e:
            logger.error(f"Error fetching investment data for dashboard: {str(e)}")
            asset_allocation_labels = ['No Data']
            asset_allocation_data = [100]
            todays_change_pct = 0.0
            todays_change_amount = 0.0
            projected_retirement_value = 0
            budget_data = {'labels': [], 'planned': [], 'actual': []}
            monthly_portfolio_data = []
            historical_data = {
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                'values': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            }
        
        # Prepare final context dictionary
        context = {
            'page_title': 'Dashboard',
            'has_plaid_data': bool(accounts),
            'total_value': investment_account_total,
            'cash_balance': cash_balance,
            'credit_balance': abs(credit_balance),
            'loan_balance': abs(loan_balance),
            'net_worth': net_worth,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'savings_rate': round(savings_rate, 1),
            'investment_accounts': investment_accounts,
            'transactions': recent_transactions,
            'current_savings': retirement_savings,
            'target_savings': target_savings,
            'retirement_progress': retirement_progress,
            'current_age': current_age,
            'asset_allocation_labels': json.dumps(asset_allocation_labels),
            'asset_allocation_data': json.dumps(asset_allocation_data),
            'todays_change_amount': todays_change_amount,
            'todays_change_pct': todays_change_pct,
            'has_investment_data': bool(investment_accounts),
            'budget_data': json.dumps(budget_data),
            'projected_retirement_value': projected_retirement_value,
            'user_profile': profile,
            'monthly_portfolio_data': json.dumps(monthly_portfolio_data),
            'historical_data': json.dumps(historical_data)
        }
        
        return render(request, 'dashboard/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        messages.error(request, f"Error loading dashboard: {str(e)}")
        try:
            # Try to render the dashboard template first
            return render(request, 'dashboard/dashboard.html', {'error': str(e), 'page_title': 'Dashboard Error', 'has_plaid_data': False})
        except Exception as template_error:
            # If that fails, fall back to the simple error template
            logger.error(f"Error rendering dashboard template: {str(template_error)}")
            return render(request, 'dashboard/dashboard_error.html', {'error': str(e), 'page_title': 'Dashboard Error'})

@login_required
def portfolio_view(request):
    """Portfolio view with detailed investment data"""
    # Get Supabase user ID directly from request.user
    supabase_id = request.user.id
    
    # Get accounts from Supabase
    adapter = SupabaseAdapter()
    accounts = adapter.get_accounts(supabase_id) if supabase_id else []
    
    # Filter for investment accounts using is_investment_account function
    investment_accounts = [account for account in accounts if is_investment_account(account)]
    
    # Calculate account totals
    total_value = sum(float(account.get('portfolio_value', 0) or float(account.get('current_balance', 0) or 0)) for account in investment_accounts)
    
    try:
        # Fetch securities and holdings data
        securities = adapter.get_securities(supabase_id)
        holdings = adapter.get_holdings(supabase_id)
        
        # Log the data counts we're working with
        logger.info(f"Found {len(securities)} securities and {len(holdings)} holdings")
        
        # Create a dictionary mapping security IDs to securities for faster lookups
        security_lookup = {}
        for security in securities:
            if 'id' in security:
                security_lookup[security['id']] = security
        
        # Group holdings by security
        security_holdings = {}
        matched_holdings_count = 0
        unmatched_holdings_count = 0
        
        for holding in holdings:
            security_id = holding.get('security_id')
            if security_id and security_id in security_lookup:
                security = security_lookup[security_id]
                matched_holdings_count += 1
                
                if security_id not in security_holdings:
                    security_holdings[security_id] = {
                        'security': security,
                        'total_quantity': 0,
                        'total_value': 0,
                        'holdings': []
                    }
                
                # Add holding to this security
                security_holdings[security_id]['holdings'].append(holding)
                
                # Add to total quantity
                quantity = float(holding.get('quantity', 0) or 0)
                security_holdings[security_id]['total_quantity'] += quantity
                
                # Add to total value
                value = float(holding.get('institution_value', 0) or 0)
                security_holdings[security_id]['total_value'] += value
            else:
                unmatched_holdings_count += 1
        
        logger.info(f"Matched holdings: {matched_holdings_count}, Unmatched: {unmatched_holdings_count}")
        
        # Create a list of formatted holdings for the template
        formatted_holdings = []
        
        # Log all security types we found
        all_types = set(security.get('type', '').lower() for security in securities if security.get('type'))
        logger.info(f"Security types in database: {all_types}")
        
        # Group holdings by security type
        values_by_type = {}
        total_holdings_value = 0
        
        # First pass: sum values by security type
        for security_id, data in security_holdings.items():
            security = data['security']
            value = data['total_value']
            
            # Determine security type (use actual type from database)
            security_type = security.get('type', '').lower() 
            
            # Use standardized categories for consistency
            if security_type in ('etf', 'exchange traded fund'):
                security_type = 'ETF'
            elif security_type in ('mutual fund', 'fund'):
                security_type = 'Mutual Fund'
            elif security_type in ('equity', 'stock'):
                security_type = 'Stock'
            elif security_type in ('fixed income', 'bond'):
                security_type = 'Bond'
            elif security_type == 'cash':
                security_type = 'Cash'
            elif security_type == 'cryptocurrency':
                security_type = 'Cryptocurrency'
            elif security_type == 'derivative':
                security_type = 'Derivative'
            elif not security_type:
                # Try to infer from name if type is missing
                name = security.get('name', '').lower()
                if 'fund' in name:
                    security_type = 'Mutual Fund'
                elif 'etf' in name:
                    security_type = 'ETF'
                elif 'bond' in name or 'treasury' in name:
                    security_type = 'Bond'
                else:
                    security_type = 'Other'
            else:
                # Capitalize for display
                security_type = security_type.title()
            
            # Add to type totals
            if security_type not in values_by_type:
                values_by_type[security_type] = 0
            values_by_type[security_type] += value
            total_holdings_value += value
            
            # Also add to formatted holdings for display
            if data['total_quantity'] > 0:
                # Calculate percentage of portfolio
                percentage = (value / total_value * 100) if total_value > 0 else 0
                
                # For demo purposes, assign a random return
                random.seed(security_id)  # Use security ID as seed for consistent results
                return_value = random.uniform(-10, 20)
                
                formatted_holdings.append({
                    'name': security.get('name', 'Unknown'),
                    'ticker_symbol': security.get('ticker_symbol', '-'),
                    'type': security_type,
                    'quantity': data['total_quantity'],
                    'price': float(security.get('close_price', 0) or 0),
                    'value': value,
                    'percentage': percentage,
                    'return': return_value
                })
        
        # Sort holdings by value (descending)
        formatted_holdings.sort(key=lambda x: x['value'], reverse=True)
        
        # Prepare asset allocation data for the chart
        asset_allocation_labels = []
        asset_allocation_data = []
        
        # Only include types with value
        for security_type, value in values_by_type.items():
            if value > 0:
                asset_allocation_labels.append(security_type)
                
                # Calculate percentage of total holdings
                percent = (value / total_holdings_value * 100) if total_holdings_value > 0 else 0
                asset_allocation_data.append(round(percent, 2))
        
        # Log what we're sending to the template
        logger.info(f"Asset allocation labels: {asset_allocation_labels}")
        logger.info(f"Asset allocation data: {asset_allocation_data}")
        logger.info(f"Total holdings value: {total_holdings_value}, Portfolio value: {total_value}")
        
        # Generate monthly portfolio value data
        monthly_portfolio_data = []
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Generate data for all months of the current year
        month_labels = []
        month_values = []
        
        for month in range(1, 13):
            month_name = datetime(current_year, month, 1).strftime('%b')  # Short month name (Jan, Feb, etc.)
            month_labels.append(month_name)
            
            # For past months, use actual data (or 0 if no data available)
            # For current month, use current portfolio value
            # For future months, use null
            if month < current_month:
                # Past month - for now, use a percentage of current value (can be replaced with actual historical data)
                # This approach simulates some growth over time
                month_growth_factor = 0.95 + (0.05 * month / current_month)  # Progressive growth toward current value
                month_value = total_value * month_growth_factor if total_value > 0 else 0
                month_values.append(round(month_value, 2))
            elif month == current_month:
                # Current month - use actual portfolio value
                month_values.append(total_value)
            else:
                # Future month - use null (chart will show a gap)
                month_values.append(None)
        
        # Historical portfolio data for chart
        historical_data = {
            'labels': month_labels,
            'values': month_values
        }
        
    except Exception as e:
        logger.error(f"Error fetching investment data: {str(e)}")
        logger.exception("Full exception details:")
        securities = []
        holdings = []
        formatted_holdings = []
        security_holdings = {}
        asset_allocation_labels = ['No Data']
        asset_allocation_data = [100]
        monthly_portfolio_data = []
        historical_data = {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'values': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        }
    
    context = {
        'page_title': 'Investment Portfolio',
        'total_value': total_value,
        'accounts': investment_accounts,
        'investment_accounts': investment_accounts,  # Duplicate for consistency with investments.html
        'securities': securities,
        'holdings': formatted_holdings,
        'asset_allocation_labels': json.dumps(asset_allocation_labels),
        'asset_allocation_data': json.dumps(asset_allocation_data),
        'monthly_portfolio_data': json.dumps(monthly_portfolio_data),
        'historical_data': json.dumps(historical_data),
        'has_investment_data': bool(investment_accounts)
    }
    
    return render(request, 'dashboard/portfolio.html', context)

@login_required
def transactions_view(request):
    """Display all transactions using Supabase data"""
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
        start_date = date(last_month_year, last_month, 1)
        end_date = date(last_month_year, last_month, last_month_days)
    
    # Get transactions from Supabase
    transactions = []
    if supabase_id:
        # Format dates for Supabase
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Get transactions with date filtering
        transactions = adapter.get_transactions(
            supabase_id, 
            start_date=start_date_str, 
            end_date=end_date_str,
            account_id=account_id if account_id else None
        )
        
        # Apply additional filtering in Python
        if category:
            transactions = [t for t in transactions if category.lower() in (t.get('category') or '').lower()]
        
        if search:
            transactions = [t for t in transactions if 
                search.lower() in (t.get('merchant_name') or '').lower() or 
                search.lower() in (t.get('name') or '').lower() or
                search.lower() in (t.get('category') or '').lower()]
    
    # Get accounts to add account names to transactions
    accounts = adapter.get_accounts(supabase_id) if supabase_id else []
    account_map = {account['id']: account for account in accounts}
    
    # Identify investment accounts
    investment_account_ids = []
    for account in accounts:
        if account.get('is_investment') or account.get('is_investment_account') or account.get('type') == 'investment':
            if 'id' in account:
                investment_account_ids.append(account['id'])
            if 'account_id' in account:
                investment_account_ids.append(account['account_id'])
    
    # Add account names to transactions
    for transaction in transactions:
        if transaction.get('account_id') in account_map:
            transaction['account_name'] = account_map[transaction['account_id']].get('name', 'Unknown Account')
        else:
            transaction['account_name'] = 'Unknown Account'
    
    # Compute spending by category
    spending_by_category = {}
    for transaction in transactions:
        category = transaction.get('category', 'Uncategorized')
        amount = float(transaction.get('amount', 0))
        # Invert the sign for spending calculation (positive amount is an expense)
        if amount < 0:  # Income is negative in Plaid's format
            continue
        
        if category in spending_by_category:
            spending_by_category[category] += amount
        else:
            spending_by_category[category] = amount
            
    # Calculate monthly cash flow for chart
    monthly_cashflow = {}
    today = datetime.now()
    
    # Get transactions for the last 5 months
    if supabase_id:
        # Calculate extended start date (5 months ago)
        extended_start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        for _ in range(4):  # Go back 4 more months
            extended_start_date = (extended_start_date - timedelta(days=1)).replace(day=1)
            
        extended_start_date_str = extended_start_date.date().isoformat()
        
        # Get all transactions for this extended period
        extended_transactions = adapter.get_transactions(
            supabase_id,
            start_date=extended_start_date_str,
            end_date=end_date_str
        )
        
        # Calculate cash flow by month
        for transaction in extended_transactions:
            if not transaction.get('date'):
                continue
                
            tx_date = datetime.strptime(transaction.get('date'), '%Y-%m-%d')
            month_name = tx_date.strftime('%B')  # Full month name
            amount = float(transaction.get('amount', 0))
            
            if month_name not in monthly_cashflow:
                monthly_cashflow[month_name] = {'inflow': 0, 'outflow': 0}
                
            if amount < 0:  # Income (negative in Plaid format)
                monthly_cashflow[month_name]['inflow'] += abs(amount)
            else:  # Expense
                monthly_cashflow[month_name]['outflow'] += amount
    
    # Get unique categories for filter dropdown
    categories = set()
    for transaction in transactions:
        if transaction.get('category'):
            categories.add(transaction.get('category'))
    
    # Paginate results
    page_number = request.GET.get('page', 1)
    paginator = Paginator(transactions, 25)  # Show 25 transactions per page
    
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'page_title': 'Transactions',
        'transactions': page_obj,
        'categories': sorted(list(categories)),
        'accounts': accounts,
        'date_filter': date_filter,
        'selected_account': account_id,
        'spending_by_category': spending_by_category,
        'monthly_cashflow': monthly_cashflow,
        'investment_account_ids': investment_account_ids
    }
    
    return render(request, 'dashboard/transactions.html', context) 