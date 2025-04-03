import os
import logging
from supabase import create_client, Client
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance: Optional[Client] = None
    _auth_instance: Optional[Client] = None  # Separate instance for authentication

    @classmethod
    def get_instance(cls) -> Client:
        """Get the Supabase client with service role for admin operations"""
        if cls._instance is None:
            if not settings.SUPABASE_URL:
                raise ValueError("Supabase URL must be set in settings")
            
            # Use service role key for admin operations
            key = settings.SUPABASE_SECRET
            
            if not key:
                logger.warning("SUPABASE_SECRET not set, falling back to SUPABASE_KEY")
                key = settings.SUPABASE_KEY
            
            cls._instance = create_client(settings.SUPABASE_URL, key)
        return cls._instance

    @classmethod
    def get_auth_instance(cls) -> Client:
        """Get the Supabase client with anon key for auth operations"""
        if cls._auth_instance is None:
            if not settings.SUPABASE_URL:
                raise ValueError("Supabase URL must be set in settings")
            
            # Use anon key for auth operations
            key = settings.SUPABASE_KEY
            
            cls._auth_instance = create_client(settings.SUPABASE_URL, key)
        return cls._auth_instance

    @classmethod
    def get_auth(cls):
        return cls.get_auth_instance().auth

    @classmethod
    def get_database(cls):
        return cls.get_instance().table

    @classmethod
    def get_storage(cls):
        return cls.get_instance().storage

def get_supabase_client(for_auth=False) -> Client:
    """
    Get a configured Supabase client.
    
    Args:
        for_auth: If True, returns a client with anon key for auth operations.
                  If False, returns a client with service role key for admin operations.
    
    Returns:
        Configured Supabase client
    """
    url = settings.SUPABASE_URL
    
    if for_auth:
        # For authentication, we use the anon key
        key = settings.SUPABASE_KEY
        logger.debug(f"Initializing Supabase auth client with URL: {url}")
    else:
        # For admin operations, we use the service role key
        key = settings.SUPABASE_SECRET
        if not key:
            logger.warning("SUPABASE_SECRET not set, falling back to SUPABASE_KEY")
            key = settings.SUPABASE_KEY
        logger.debug(f"Initializing Supabase admin client with URL: {url}")
    
    if not url or not key:
        raise ValueError("Supabase URL and key must be configured in settings")
    
    return create_client(url, key) 