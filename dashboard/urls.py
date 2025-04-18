"""
URL patterns for the dashboard app.
"""
from django.urls import path
from templates.views.dashboard_views import (
    dashboard_view,
    portfolio_view,
)
from .views.transactions_view import all_transactions_view, regular_transactions_view
from .views.goals_view import goals_view, create_goal, update_goal, delete_goal, add_funds
from .views.support_view import support_view
from .views.planning_view import planning_view, calculate_retirement, save_retirement_profile
from .views.budgeting_view import budgeting_view
from .views.plaid_connection_view import (
    connect_bank_view, 
    create_link_token_view, 
    exchange_public_token_view,
    manual_refresh_view
)
from dashboard.views import debug_view
from .views.subscription_view import subscription_view
from .views.mobile_plaid_view import (
    create_link_token,
    exchange_public_token,
    get_plaid_items,
    get_accounts,
    get_transactions,
    manual_refresh,
)

app_name = 'dashboard'

urlpatterns = [
    # Dashboard views
    path('', dashboard_view, name='dashboard'),
    path('portfolio/', portfolio_view, name='portfolio'),
    path('transactions/', regular_transactions_view, name='transactions'),
    path('all-transactions/', all_transactions_view, name='all_transactions'),
    path('goals/', goals_view, name='goals'),
    path('support/', support_view, name='support'),
    path('planning/', planning_view, name='planning'),
    path('budgeting/', budgeting_view, name='budgeting'),
    path('subscription/', subscription_view, name='subscription'),
    
    # Retirement planning endpoints
    path('calculate-retirement/', calculate_retirement, name='calculate_retirement'),
    path('save-retirement-profile/', save_retirement_profile, name='save_retirement_profile'),
    
    # Plaid connection views
    path('connect-bank/', connect_bank_view, name='connect_bank'),
    path('api/plaid/create-link-token/', create_link_token_view, name='create_link_token'),
    path('api/plaid/exchange-public-token/', exchange_public_token_view, name='exchange_public_token'),
    path('api/plaid/refresh/', manual_refresh_view, name='manual_refresh'),
    
    # Mobile API endpoints
    path('api/mobile/plaid/create-link-token/', create_link_token, name='mobile_create_link_token'),
    path('api/mobile/plaid/exchange-public-token/', exchange_public_token, name='mobile_exchange_public_token'),
    path('api/mobile/plaid/get-plaid-items/', get_plaid_items, name='mobile_get_plaid_items'),
    path('api/mobile/plaid/get-accounts/', get_accounts, name='mobile_get_accounts'),
    path('api/mobile/plaid/get-transactions/', get_transactions, name='mobile_get_transactions'),
    path('api/mobile/plaid/refresh/', manual_refresh, name='mobile_manual_refresh'),
    
    # Financial Goals API endpoints
    path('api/goals/create/', create_goal, name='create_goal'),
    path('api/goals/update/<uuid:goal_id>/', update_goal, name='update_goal'),
    path('api/goals/delete/<uuid:goal_id>/', delete_goal, name='delete_goal'),
    path('api/goals/add-funds/<uuid:goal_id>/', add_funds, name='add_funds'),

    # Debug views
    path('debug/transactions/', debug_view.debug_transactions, name='debug_transactions'),
    path('debug/transaction-display/', debug_view.debug_transaction_display, name='debug_transaction_display'),
    path('debug/transaction-analysis/', debug_view.transaction_debug, name='transaction_debug'),
    path('debug/sync-transactions/', debug_view.manual_transaction_sync, name='manual_transaction_sync'),
    path('debug/fixed-date-sync/', debug_view.fixed_date_transaction_sync, name='fixed_date_transaction_sync'),
] 