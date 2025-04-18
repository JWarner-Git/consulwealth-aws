"""
Django settings for ConsulWealth project.
This file contains the minimal settings required for the application.
"""
import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-dev')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Update allowed hosts for AWS Amplify
ALLOWED_HOSTS = [
    'consulwealth.com',
    'www.consulwealth.com',
    '52.0.88.97',  # Load balancer IP
    'consulwealth.us-east-1.elasticbeanstalk.com',
    '.elasticbeanstalk.com',
    '172.31.87.107',  # EC2 instance private IP for health checks
    '172.31.*',      # All internal AWS IPs in this subnet
    '10.0.0.0/8',    # Standard private network range
    '172.16.0.0/12', # Standard private network range
    '192.168.0.0/16',# Standard private network range
    '*',             # Accept all hosts during troubleshooting - remove in production
    'localhost',
    '127.0.0.1',
]

# Allow all subdomains of amplifyapp.com and elasticbeanstalk.com
if 'amplifyapp.com' in ALLOWED_HOSTS:
    from fnmatch import fnmatch
    class GlobalSiteMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response
        def __call__(self, request):
            host = request.get_host()
            if (fnmatch(host, '*.amplifyapp.com') or 
                fnmatch(host, '*.consulwealth.com') or 
                fnmatch(host, '*.elasticbeanstalk.com') or
                host.endswith('.elb.amazonaws.com')):
                ALLOWED_HOSTS.append(host)
            return self.get_response(request)

# Add CSRF trusted origins for AWS Amplify
CSRF_TRUSTED_ORIGINS = [
    'https://*.amplifyapp.com', 
    'https://*.consulwealth.com', 
    'https://consulwealth.com', 
    'http://*.consulwealth.com', 
    'http://consulwealth.com',
    'https://*.elasticbeanstalk.com',
    'http://*.elasticbeanstalk.com',
    'https://consulwealth.us-east-1.elasticbeanstalk.com',
    'http://consulwealth.us-east-1.elasticbeanstalk.com',
]

# Application definition
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Added for number/date formatting in templates
    
    # Project apps
    'users',
    'dashboard',
    'supabase_integration',
    'subscriptions',
    
    # Third-party apps
    'rest_framework',
    'whitenoise.runserver_nostatic',
    'corsheaders',  # Add cors headers app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add whitenoise for static files
    'corsheaders.middleware.CorsMiddleware',  # Add CORS middleware early in the list
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Include both middlewares - Django's is needed for admin, ours for the app
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'supabase_integration.middleware.SupabaseAuthMiddleware',
    'subscriptions.middleware.SubscriptionRequiredMiddleware',  # Subscription check middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add AWS Amplify hostname middleware conditionally
if 'amplifyapp.com' in ALLOWED_HOSTS:
    MIDDLEWARE.insert(0, 'core.settings.GlobalSiteMiddleware')

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://consulwealth.com',
    'https://www.consulwealth.com',
    'http://localhost:3000',  # For local development
    'http://localhost:8000',
]

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Additional CORS settings
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# Use DATABASE_URL environment variable for production database
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL')
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom user model - Required for Django admin but is just a shadow of Supabase data
# Django users are only created as read-only shadows of Supabase users
AUTH_USER_MODEL = 'users.User'

# Authentication backend for shadow user approach
# The SupabaseAuthBackend will authenticate against Supabase and create/update shadow users
AUTHENTICATION_BACKENDS = [
    'users.auth.SupabaseAuthBackend',
    # Keeping Django's backend for admin access during transition
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Make sure the static directory exists
if not os.path.exists(os.path.join(BASE_DIR, 'static')):
    os.makedirs(os.path.join(BASE_DIR, 'static'))
if not os.path.exists(STATIC_ROOT):
    os.makedirs(STATIC_ROOT)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Add storage settings for AWS if available
if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    # S3 static settings
    STATIC_LOCATION = 'static'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/'
    STATICFILES_STORAGE = 'core.storage_backends.StaticStorage'

# Supabase settings - Load from environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SECRET = os.environ.get('SUPABASE_SERVICE_KEY')  # Using service key for admin operations

# Plaid settings - Load from environment variables 
PLAID_CLIENT_ID = os.environ.get('PLAID_CLIENT_ID')
PLAID_SECRET = os.environ.get('PLAID_SECRET')
PLAID_ENVIRONMENT = os.environ.get('PLAID_ENVIRONMENT', 'sandbox')
PLAID_DEV_MODE = False  # Disabled - enforce refresh restrictions

# Stripe settings
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PREMIUM_PRICE_ID = os.environ.get('STRIPE_PREMIUM_PRICE_ID')  # Use production price ID

# Print debugging info for Supabase settings (only in debug mode)
if DEBUG:
    print(f"Loaded SUPABASE_URL: {'Set' if SUPABASE_URL else 'NOT SET'}")
    print(f"Loaded SUPABASE_KEY: {'Set' if SUPABASE_KEY else 'NOT SET'}")
    print(f"Loaded SUPABASE_SECRET: {'Set' if SUPABASE_SECRET else 'NOT SET'}")
    print(f"Loaded PLAID_CLIENT_ID: {'Set' if PLAID_CLIENT_ID else 'NOT SET'}")
    print(f"Loaded PLAID_SECRET: {'Set' if PLAID_SECRET else 'NOT SET'}")
    print(f"Loaded PLAID_ENVIRONMENT: {PLAID_ENVIRONMENT}")
    print(f"Plaid Dev Mode: {PLAID_DEV_MODE}")
    print(f"Loaded STRIPE_PUBLISHABLE_KEY: {'Set' if STRIPE_PUBLISHABLE_KEY else 'NOT SET'}")
    print(f"Loaded STRIPE_SECRET_KEY: {'Set' if STRIPE_SECRET_KEY else 'NOT SET'}")
    print(f"Using Stripe Price ID: {STRIPE_PREMIUM_PRICE_ID}")

# Supabase auth settings
SUPABASE_AUTH_HEADER = 'HTTP_AUTHORIZATION'
SUPABASE_AUTH_TOKEN_COOKIE = 'supabase_auth_token'
SUPABASE_REFRESH_TOKEN_COOKIE = 'supabase_refresh_token'

# Shadow User Synchronization Settings
# Configure how often to sync users and whether to do it automatically
SUPABASE_AUTO_SYNC_USERS = True  # Automatically sync on each request
SUPABASE_SYNC_INTERVAL = 86400   # 24 hours in seconds

# Login redirect
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'supabase_integration': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'users': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Add debug settings for development mode
if DEBUG:
    # Debug static file handling
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    WHITENOISE_USE_FINDERS = True
    
    # Add debug toolbar settings if needed
    # INSTALLED_APPS.append('debug_toolbar')
    # MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    # INTERNAL_IPS = ['127.0.0.1']
else:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


