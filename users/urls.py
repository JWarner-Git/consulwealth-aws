from django.urls import path
from django.shortcuts import redirect
from django.contrib.auth import views as django_auth_views
from .views import auth_views, plaid_views

app_name = 'users'

def redirect_to_login(request):
    return redirect('login')

urlpatterns = [
    # Root URL redirect
    path('', redirect_to_login, name='users-index'),
    
    # Auth URLs
    path('register/', auth_views.register, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('verify-email/<uuid:token>/', auth_views.verify_email, name='verify_email'),
    path('resend-verification/', auth_views.resend_verification, name='resend_verification'),
    
    # Password Reset URLs
    path('password-reset/',
         django_auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         django_auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         django_auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         django_auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),
    
    # Plaid URLs - Modern implementation
    path('api/plaid/create-link-token/', plaid_views.create_link_token, name='create_link_token'),
    path('api/plaid/exchange-public-token/', plaid_views.exchange_public_token, name='exchange_public_token'),
    
    # Plaid UI Pages
    path('connect/', plaid_views.simple_plaid_link, name='simple_plaid_link'),
    path('plaid-test/', plaid_views.standalone_plaid_test, name='standalone_plaid_test'),
    
    # Legacy compatibility
    path('plaid/link/', plaid_views.simple_plaid_link, name='plaid_link'),
    path('test-plaid/', plaid_views.simple_plaid_link, name='test_plaid_link'),
] 