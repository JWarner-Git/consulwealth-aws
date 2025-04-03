"""
URL patterns for the dashboard app.
"""
from django.urls import path
from templates.views.dashboard_views import (
    dashboard_view,
    portfolio_view,
)
from .views.transactions_view import all_transactions_view, regular_transactions_view
from .views.goals_view import goals_view
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

    # Debug views
    path('debug/transactions/', debug_view.debug_transactions, name='debug_transactions'),
    path('debug/transaction-display/', debug_view.debug_transaction_display, name='debug_transaction_display'),
    path('debug/transaction-analysis/', debug_view.transaction_debug, name='transaction_debug'),
    path('debug/sync-transactions/', debug_view.manual_transaction_sync, name='manual_transaction_sync'),
    path('debug/fixed-date-sync/', debug_view.fixed_date_transaction_sync, name='fixed_date_transaction_sync'),
] 