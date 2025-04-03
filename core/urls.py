"""
URL Configuration for the ConsulWealth project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from supabase_integration.views.profile_views import profile_view
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Welcome page (accessible at /welcome/)
    path('welcome/', TemplateView.as_view(template_name='welcome.html'), name='welcome'),
    
    # Dashboard routes
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    
    # User authentication routes - Supabase-only implementation
    path('auth/', include('supabase_integration.urls', namespace='supabase')),
    
    # Profile route
    path('profile/', profile_view, name='profile'),
    
    # Subscription routes
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    
    # Using these two lines to redirect to our Supabase login instead of Django's login
    path('accounts/login/', RedirectView.as_view(url='/auth/login/', permanent=False)),
    path('login/', RedirectView.as_view(url='/auth/login/', permanent=False)),
    
    # Redirect root to login page
    path('', RedirectView.as_view(url='/auth/login/', permanent=False)),
]
