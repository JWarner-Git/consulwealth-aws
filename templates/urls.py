"""
URL patterns for the dashboard app.
"""
from django.urls import path
from .views.dashboard_views import (
    dashboard_view,
    portfolio_view,
    transactions_view
)

app_name = 'dashboard'

urlpatterns = [
    # Dashboard views
    path('', dashboard_view, name='dashboard'),
    path('portfolio/', portfolio_view, name='portfolio'),
    path('transactions/', transactions_view, name='transactions'),
] 