"""
Helper functions to assist with the transition from Django models to Supabase.

These functions provide utilities for working with Supabase data structures
and converting between Django models and Supabase records.
"""
from typing import Dict, Any, List, Optional, Union, Type
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal, InvalidOperation
import datetime
from .adapter import SupabaseAdapter
from .services import SupabaseService

User = get_user_model()

def safe_decimal(value: Any) -> Decimal:
    """
    Safely convert a value to Decimal, returning 0 if conversion fails.
    
    Args:
        value: The value to convert to Decimal
        
    Returns:
        Decimal value, or 0 if conversion fails
    """
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0')

def safe_date(value: Any) -> Optional[datetime.date]:
    """
    Safely convert a string to a date, returning None if conversion fails.
    
    Args:
        value: The value to convert to date
        
    Returns:
        datetime.date value, or None if conversion fails
    """
    if isinstance(value, datetime.date):
        return value
        
    if not value:
        return None
        
    try:
        # Try ISO format (YYYY-MM-DD)
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        try:
            # Try with time component (YYYY-MM-DD HH:MM:SS)
            dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.date()
        except (ValueError, TypeError, AttributeError):
            return None

def safe_bool(value: Any) -> bool:
    """
    Safely convert a value to boolean.
    
    Args:
        value: The value to convert to boolean
        
    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
        
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 't', 'y')
        
    return bool(value)

def model_to_dict(instance: models.Model) -> Dict[str, Any]:
    """
    Convert a Django model instance to a dictionary suitable for Supabase.
    Similar to Django's model_to_dict but customized for Supabase.
    
    Args:
        instance: Django model instance
        
    Returns:
        Dictionary representation of the model
    """
    data = {}
    
    # Get all fields from the model
    for field in instance._meta.fields:
        field_name = field.name
        field_value = getattr(instance, field_name)
        
        # Skip empty values
        if field_value is None:
            continue
            
        # Handle special types
        if isinstance(field_value, Decimal):
            data[field_name] = float(field_value)
        elif isinstance(field_value, datetime.datetime):
            data[field_name] = field_value.isoformat()
        elif isinstance(field_value, datetime.date):
            data[field_name] = field_value.isoformat()
        elif isinstance(field_value, models.Model):
            # For foreign keys, just store the ID
            data[field_name] = str(field_value.pk)
        else:
            data[field_name] = field_value
    
    return data

def dict_to_model(data: Dict[str, Any], model_class: Type[models.Model]) -> models.Model:
    """
    Convert a dictionary from Supabase to a Django model instance.
    
    Args:
        data: Dictionary from Supabase
        model_class: Django model class
        
    Returns:
        Django model instance
    """
    instance = model_class()
    
    # Get all fields from the model
    for field in instance._meta.fields:
        field_name = field.name
        
        # Skip if field not in data
        if field_name not in data:
            continue
            
        field_value = data[field_name]
        
        # Handle None values
        if field_value is None:
            setattr(instance, field_name, None)
            continue
            
        # Handle different field types
        field_type = field.get_internal_type()
        
        if field_type == 'DecimalField':
            setattr(instance, field_name, safe_decimal(field_value))
        elif field_type == 'DateField':
            setattr(instance, field_name, safe_date(field_value))
        elif field_type == 'BooleanField':
            setattr(instance, field_name, safe_bool(field_value))
        elif field_type in ('ForeignKey', 'OneToOneField'):
            # For foreign keys, we need to get the related model
            related_model = field.related_model
            if field_name == 'user':
                # Special handling for User foreign keys
                try:
                    user = User.objects.get(pk=field_value)
                    setattr(instance, field_name, user)
                except User.DoesNotExist:
                    pass
            else:
                # For other foreign keys, just set the ID
                setattr(instance, field_name + '_id', field_value)
        else:
            # For other field types, just set the value
            setattr(instance, field_name, field_value)
    
    return instance

def get_object_or_none(model_class: Type[models.Model], **kwargs) -> Optional[models.Model]:
    """
    Similar to Django's get_object_or_404, but returns None instead of raising Http404.
    
    Args:
        model_class: Django model class
        **kwargs: Lookup parameters
        
    Returns:
        Django model instance or None
    """
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None

def ensure_supabase_user(user: User) -> Optional[str]:
    """
    Ensure that a Django user has a corresponding Supabase user.
    If not, create one.
    
    Args:
        user: Django user
        
    Returns:
        Supabase user ID if successful, None otherwise
    """
    # First check if the user already has a Supabase ID
    supabase_id = SupabaseService.get_supabase_id_for_user(user)
    if supabase_id:
        return supabase_id
        
    # If not, create a Supabase user
    return SupabaseService.sync_user_to_supabase(user)

def get_user_by_supabase_id(supabase_id: str) -> Optional[User]:
    """
    Get a Django user by Supabase ID.
    
    Args:
        supabase_id: Supabase user ID
        
    Returns:
        Django user or None
    """
    try:
        # Try to get the user from SupabaseSync
        from banking.models import SupabaseSync
        sync = SupabaseSync.objects.get(supabase_id=supabase_id)
        return sync.user
    except:
        # If that fails, try to get by email
        adapter = SupabaseAdapter()
        profile = adapter.get_profile(supabase_id)
        if profile and 'email' in profile:
            try:
                return User.objects.get(email=profile['email'])
            except User.DoesNotExist:
                return None
        return None 