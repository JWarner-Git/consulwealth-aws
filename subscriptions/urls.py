from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('create/', views.create_subscription, name='create_subscription'),
    path('status/', views.subscription_status, name='subscription_status'),
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('debug-user-id/', views.debug_user_id, name='debug_user_id'),
    path('update-profile-to-premium/', views.update_profile_to_premium, name='update_profile_to_premium'),
    path('subscribe/', views.subscription_page, name='subscription_page'),
] 