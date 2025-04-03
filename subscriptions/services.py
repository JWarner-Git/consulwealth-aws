import stripe
import logging
from django.conf import settings
from supabase_integration.adapter import SupabaseAdapter
from datetime import datetime
from typing import Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)

class StripeService:
    """
    Service class to handle Stripe API interactions, using Supabase as the data store.
    Following the same architectural pattern as PlaidService.
    """
    
    def __init__(self):
        """Initialize the StripeService"""
        self.adapter = SupabaseAdapter()
        
        # Stripe API credentials
        self.publishable_key = settings.STRIPE_PUBLISHABLE_KEY
        self.secret_key = settings.STRIPE_SECRET_KEY
        
        # Use the price ID from settings
        self.premium_price_id = settings.STRIPE_PREMIUM_PRICE_ID
        logger.info(f"Using Stripe price ID: {self.premium_price_id}")
        
        if not self.premium_price_id:
            logger.error("NO PRICE ID FOUND IN SETTINGS! Check your environment variables.")
        
        # Initialize Stripe API
        stripe.api_key = self.secret_key
        
        logger.info(f"Initializing Stripe Service with price ID: {self.premium_price_id}")
    
    def create_subscription(self, user, token, plan='premium'):
        """
        Create a new Stripe subscription for the user
        
        Args:
            user: The user object
            token: The Stripe token from the frontend
            plan: The subscription plan (default: 'premium')
            
        Returns:
            dict: Subscription data if successful
            None: If there was an error
        """
        try:
            logger.info(f"Creating subscription for user {user.id}, plan: {plan}")
            
            # Get the user ID as string - essential for proper database operations
            user_id = str(user.id)
            
            # Create or retrieve a customer
            customer = self._get_or_create_customer(user, token)
            if not customer:
                logger.error("Failed to get or create Stripe customer")
                return None
                
            # Create the subscription in Stripe
            logger.info(f"Creating Stripe subscription with price ID: {self.premium_price_id}")
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {
                        'price': self.premium_price_id,
                    },
                ],
            )
            
            logger.info(f"Stripe subscription created: {stripe_subscription.id}")
            
            # Store subscription in local database
            subscription_data = self._store_subscription(user, customer.id, stripe_subscription.id, plan, stripe_subscription.status)
            
            # Update the user's profile in Supabase
            from django.utils import timezone
            
            # Default to 30 days from now if can't get from Stripe
            end_date = (timezone.now() + timezone.timedelta(days=30)).isoformat()
            
            try:
                # Safely access the period end time
                if hasattr(stripe_subscription, 'current_period_end') and stripe_subscription.current_period_end:
                    end_date = timezone.datetime.fromtimestamp(
                        int(stripe_subscription.current_period_end),
                        tz=timezone.get_current_timezone()
                    ).isoformat()
                    logger.info(f"Using subscription end date from Stripe: {end_date}")
            except Exception as e:
                logger.warning(f"Error getting subscription end date from Stripe: {str(e)}")
                # Use the default set above
            
            profile_data = {
                'is_premium_subscriber': True,
                'subscription_plan': plan,
                'subscription_status': stripe_subscription.status,
                'subscription_end_date': end_date
            }
            
            # Use the adapter to update the profile properly
            success = self.adapter.update_profile(user_id, profile_data)
            logger.info(f"Profile update result: {success}")
            
            return {
                'id': stripe_subscription.id,
                'status': stripe_subscription.status,
                'current_period_end': getattr(stripe_subscription, 'current_period_end', None),
            }
        
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return None
    
    def _get_or_create_customer(self, user, token):
        """
        Get an existing Stripe customer or create a new one
        
        Args:
            user: The user object
            token: The Stripe token
            
        Returns:
            Stripe Customer object if successful
            None if there was an error
        """
        try:
            # First check if user already has a subscription record
            user_id = str(user.id)
            from .models import Subscription
            
            # Get Django User instance
            django_user = self._get_django_user(user)
            if not django_user:
                logger.error("Could not get Django User instance")
                return None
            
            try:
                # Look up subscription using Django user
                subscription = Subscription.objects.filter(user=django_user).first()
                
                # If there's a customer ID, retrieve the customer
                if subscription and subscription.stripe_customer_id:
                    customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                    logger.info(f"Retrieved existing Stripe customer: {customer.id}")
                    return customer
            except Exception as e:
                logger.info(f"No existing subscription found or error retrieving it: {str(e)}")
                
            # Create a new customer
            name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.email
            customer = stripe.Customer.create(
                email=user.email,
                source=token,
                name=name
            )
            
            logger.info(f"Created new Stripe customer: {customer.id}")
            return customer
            
        except Exception as e:
            logger.error(f"Error getting or creating customer: {str(e)}")
            return None
    
    def _get_django_user(self, user):
        """
        Get a Django User instance from a SupabaseUser or Django User
        
        Args:
            user: Either a SupabaseUser or Django User instance
            
        Returns:
            Django User instance if found, None otherwise
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            # If it's already a Django User, return it
            if isinstance(user, User):
                return user
                
            # If it's a SupabaseUser from middleware, get Django user by Supabase ID
            from supabase_integration.middleware import SupabaseUser
            if isinstance(user, SupabaseUser):
                supabase_id = user.id
                try:
                    # Try to get by supabase_id directly
                    django_user = User.objects.get(supabase_id=supabase_id)
                    logger.info(f"Found Django user by Supabase ID: {django_user}")
                    return django_user
                except User.DoesNotExist:
                    # Try by email
                    try:
                        django_user = User.objects.get(email=user.email)
                        logger.info(f"Found Django user by email: {django_user}")
                        return django_user
                    except User.DoesNotExist:
                        # Create a shadow user
                        username = user.email.split('@')[0]
                        base_username = username
                        counter = 1
                        
                        # Ensure username is unique
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}_{counter}"
                            counter += 1
                        
                        # Create a shadow user
                        django_user = User.objects.create(
                            username=username,
                            email=user.email,
                            supabase_id=supabase_id
                        )
                        django_user.set_unusable_password()
                        django_user.save()
                        logger.info(f"Created shadow Django user for subscription: {django_user}")
                        return django_user
            
            # Unknown user type
            logger.error(f"Unknown user type: {type(user)}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Django user: {str(e)}")
            return None
    
    def _store_subscription(self, user, customer_id, subscription_id, plan, status):
        """
        Store subscription data in the Django database
        
        Args:
            user: The user object
            customer_id: The Stripe customer ID
            subscription_id: The Stripe subscription ID
            plan: The subscription plan
            status: The subscription status
            
        Returns:
            Subscription object if successful
            None if there was an error
        """
        try:
            from .models import Subscription
            
            # Get Django User instance from the user object
            django_user = self._get_django_user(user)
            if not django_user:
                logger.error("Could not get Django User instance")
                return None
            
            # Get the Stripe subscription to get accurate period times
            period_start = timezone.now()
            period_end = timezone.now() + timezone.timedelta(days=30)
            
            try:
                # Retrieve subscription from Stripe
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                logger.info(f"Retrieved Stripe subscription: {subscription_id}")
                
                # Log the subscription data for debugging
                logger.debug(f"Stripe subscription data: {stripe_subscription}")
                
                # Safely access the period times
                if hasattr(stripe_subscription, 'current_period_start') and stripe_subscription.current_period_start:
                    period_start = timezone.datetime.fromtimestamp(
                        int(stripe_subscription.current_period_start), 
                        tz=timezone.get_current_timezone()
                    )
                    logger.info(f"Using period start from Stripe: {period_start}")
                else:
                    logger.warning("current_period_start not found in Stripe subscription, using default")
                
                if hasattr(stripe_subscription, 'current_period_end') and stripe_subscription.current_period_end:
                    period_end = timezone.datetime.fromtimestamp(
                        int(stripe_subscription.current_period_end),
                        tz=timezone.get_current_timezone()
                    )
                    logger.info(f"Using period end from Stripe: {period_end}")
                else:
                    logger.warning("current_period_end not found in Stripe subscription, using default")
                    
            except Exception as e:
                logger.warning(f"Could not get period times from Stripe, using defaults: {str(e)}")
                # Default values already set above
                
            # Check for existing subscription using the Django user
            try:
                subscription = Subscription.objects.filter(user=django_user).first()
                if subscription:
                    subscription.stripe_customer_id = customer_id
                    subscription.stripe_subscription_id = subscription_id
                    subscription.plan = plan
                    subscription.status = status
                    subscription.current_period_start = period_start
                    subscription.current_period_end = period_end
                    subscription.save()
                    logger.info(f"Updated existing subscription record for user {django_user.id}")
                else:
                    # Create new subscription with the Django user
                    subscription = Subscription.objects.create(
                        user=django_user,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                        plan=plan,
                        status=status,
                        current_period_start=period_start,
                        current_period_end=period_end
                    )
                    logger.info(f"Created new subscription record for user {django_user.id}")
            except Exception as e:
                logger.error(f"Error handling subscription record: {str(e)}")
                # Create new subscription as fallback with the Django user
                try:
                    subscription = Subscription.objects.create(
                        user=django_user,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                        plan=plan,
                        status=status,
                        current_period_start=period_start,
                        current_period_end=period_end
                    )
                    logger.info(f"Created new subscription record for user {django_user.id} after error")
                except Exception as inner_e:
                    logger.error(f"Failed to create subscription record: {str(inner_e)}")
                    return None
            
            return subscription
        
        except Exception as e:
            logger.error(f"Error storing subscription: {str(e)}")
            return None
    
    def get_subscription_status(self, user):
        """
        Get the subscription status for a user
        
        Args:
            user: The user object
            
        Returns:
            dict: Subscription status data
        """
        try:
            user_id = str(user.id)
            from .models import Subscription
            
            # Get Django User instance
            django_user = self._get_django_user(user)
            if not django_user:
                logger.error("Could not get Django User instance")
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            try:
                subscription = Subscription.objects.filter(user=django_user).first()
                if subscription:
                    return {
                        'success': True,
                        'has_subscription': True,
                        'status': subscription.status,
                        'plan': subscription.plan,
                        'is_active': subscription.is_active,
                        'current_period_end': subscription.current_period_end,
                        'cancel_at_period_end': subscription.cancel_at_period_end
                    }
                else:
                    return {
                        'success': True,
                        'has_subscription': False
                    }
            except Exception as e:
                logger.error(f"Error retrieving subscription: {str(e)}")
                return {
                    'success': True,
                    'has_subscription': False,
                    'error': str(e)
                }
        
        except Exception as e:
            logger.error(f"Error getting subscription status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_subscription(self, user):
        """
        Cancel a user's subscription
        
        Args:
            user: The user object
            
        Returns:
            dict: Result of the cancellation
        """
        try:
            user_id = str(user.id)
            from .models import Subscription
            
            # Get Django User instance
            django_user = self._get_django_user(user)
            if not django_user:
                logger.error("Could not get Django User instance")
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            try:
                subscription = Subscription.objects.filter(user=django_user).first()
                
                if subscription and subscription.stripe_subscription_id:
                    # Cancel the subscription in Stripe
                    stripe_subscription = stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
                    
                    # Update the subscription record
                    subscription.cancel_at_period_end = True
                    subscription.save()
                    
                    # Update the user's profile in Supabase
                    profile_data = {
                        'subscription_status': 'canceled'
                    }
                    
                    self.adapter.update_profile(user_id, profile_data)
                    
                    return {
                        'success': True,
                        'cancel_at_period_end': True,
                        'current_period_end': subscription.current_period_end
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No active subscription found'
                    }
            except Exception as e:
                logger.error(f"Error retrieving subscription for cancellation: {str(e)}")
                return {
                    'success': False,
                    'error': str(e)
                }
        
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_profile_to_premium(self, user):
        """
        Manual method to update a user's profile to premium status
        
        Args:
            user: The user object
            
        Returns:
            bool: Success status
        """
        try:
            # Get user ID as string
            user_id = str(user.id)
            logger.info(f"Manually updating profile for user {user_id} to premium status")
            
            # Get Django User instance
            django_user = self._get_django_user(user)
            if not django_user:
                logger.error("Could not get Django User instance")
                return False
            
            # Get existing subscription if available
            from .models import Subscription
            from django.utils import timezone
            
            try:
                # Use the Django user object
                subscription = Subscription.objects.filter(user=django_user).first()
                
                if subscription:
                    status = subscription.status
                    end_date = subscription.current_period_end.isoformat() if subscription.current_period_end else None
                else:
                    status = 'active'
                    # Use timezone-aware datetime
                    future_date = timezone.now().replace(year=timezone.now().year + 1)
                    end_date = future_date.isoformat()
            except Exception as e:
                logger.error(f"Error retrieving subscription: {str(e)}")
                status = 'active'
                # Use timezone-aware datetime
                future_date = timezone.now().replace(year=timezone.now().year + 1)
                end_date = future_date.isoformat()
            
            # Prepare profile data
            profile_data = {
                'is_premium_subscriber': True,
                'subscription_plan': 'premium',
                'subscription_status': status,
                'subscription_end_date': end_date
            }
            
            # Use the adapter to update the profile properly
            success = self.adapter.update_profile(user_id, profile_data)
            logger.info(f"Manual profile update result: {success}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error updating profile to premium: {str(e)}")
            return False 