"""
User model for the application.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)

class User(AbstractUser):
    """
    Custom user model that serves as a shadow of Supabase user data.
    
    This model is kept minimal, with most user data stored in Supabase.
    Django users are only created as read-only shadows of Supabase users,
    which enables Django admin and other Django features to work while
    Supabase remains the source of truth.
    """
    # Basic profile fields (minimal subset)
    date_of_birth = models.DateField(null=True, blank=True)
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    target_retirement_savings = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Supabase ID field (store it directly in the User model)
    supabase_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    last_synced = models.DateTimeField(auto_now=True)
    
    # Track when this shadow user was last validated against Supabase
    last_supabase_validation = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.username} (Shadow: {self.supabase_id})"
    
    def get_supabase_profile(self):
        """
        Get the user's Supabase profile.
        """
        if not self.supabase_id:
            return None
            
        try:
            # Import here to avoid circular imports
            from supabase_integration.services import SupabaseService
            service = SupabaseService()
            return service.get_user_data(self.supabase_id)
        except Exception as e:
            logger.error(f"Error fetching Supabase profile: {str(e)}")
            return None
    
    def refresh_from_supabase(self):
        """
        Refresh shadow user from Supabase data.
        This ensures the shadow user stays in sync with Supabase.
        """
        if not self.supabase_id:
            return False
            
        try:
            # Import here to avoid circular imports
            from supabase_integration.services import SupabaseService
            
            service = SupabaseService()
            supabase_user = service.get_user_data(self.supabase_id)
            
            if not supabase_user:
                logger.warning(f"Supabase user {self.supabase_id} no longer exists")
                return False
                
            # Update basic fields
            self.email = supabase_user.email
            
            # Update metadata fields if available
            user_metadata = supabase_user.user_metadata or {}
            if 'date_of_birth' in user_metadata:
                self.date_of_birth = user_metadata.get('date_of_birth')
                
            if 'annual_income' in user_metadata:
                self.annual_income = user_metadata.get('annual_income')
                
            if 'target_retirement_savings' in user_metadata:
                self.target_retirement_savings = user_metadata.get('target_retirement_savings')
                
            # Update staff status based on admin role
            self.is_staff = user_metadata.get('is_admin', False)
            
            # Update last validation time
            self.last_supabase_validation = timezone.now()
            
            self.save()
            logger.info(f"Shadow user {self.username} refreshed from Supabase")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing from Supabase: {str(e)}")
            return False
