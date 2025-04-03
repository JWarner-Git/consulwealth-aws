"""
URL patterns for Supabase authentication.
"""
from django.urls import path
from .views.auth_views import login_view, signup_view, logout_view, token_refresh

app_name = 'supabase'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('token/refresh/', token_refresh, name='token_refresh'),
] 