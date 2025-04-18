"""
Production settings for Elastic Beanstalk deployment
"""
import os
import socket
from .settings import *

# Debug should be False in production
DEBUG = False

# Static files configuration - optimized for Elastic Beanstalk
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Ensure static directories exist
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Create static directories if they don't exist
if not os.path.exists(os.path.join(BASE_DIR, 'static')):
    os.makedirs(os.path.join(BASE_DIR, 'static'), exist_ok=True)
if not os.path.exists(STATIC_ROOT):
    os.makedirs(STATIC_ROOT, exist_ok=True)

# Use WhiteNoise for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings - allow HTTP for health checks
SECURE_SSL_REDIRECT = False  # Let Elastic Beanstalk handle SSL
SESSION_COOKIE_SECURE = False  # Set to False for HTTP health checks
CSRF_COOKIE_SECURE = False  # Set to False for HTTP health checks
SECURE_HSTS_SECONDS = 0  # Disable HSTS for Elastic Beanstalk
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Update CSRF for Elastic Beanstalk
CSRF_TRUSTED_ORIGINS = [
    'https://*.elasticbeanstalk.com',
    'https://*.consulwealth.com',
    'https://consulwealth.com',
    'http://*.elasticbeanstalk.com',
    'http://*.consulwealth.com',
    'http://consulwealth.com',
]

# Update allowed hosts for Elastic Beanstalk - replace the ALLOWED_HOSTS from settings.py
ALLOWED_HOSTS = [
    '.elasticbeanstalk.com',
    '.consulwealth.com',
    'consulwealth.com',
    'localhost',
    '127.0.0.1',
    '172.31.87.107',  # EC2 instance private IP
    '172.31.*',       # Cover all possible internal AWS IPs
    '10.0.0.0/8',     # Standard private network range
    '172.16.0.0/12',  # Standard private network range
    '192.168.0.0/16', # Standard private network range
]

# Add current hostname and IP to ALLOWED_HOSTS
hostname = socket.gethostname()
try:
    ALLOWED_HOSTS.append(socket.gethostbyname(hostname))
except:
    pass

# Add wildcard for all IP addresses during deployment troubleshooting
ALLOWED_HOSTS.append('*')  # Remove this in production once everything works

# Simplified logging for Elastic Beanstalk
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
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/app-debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        '': {  # Root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# Make sure middleware is properly ordered
if 'whitenoise.middleware.WhiteNoiseMiddleware' in MIDDLEWARE:
    # Ensure WhiteNoise comes after security middleware
    MIDDLEWARE = [m for m in MIDDLEWARE if m != 'whitenoise.middleware.WhiteNoiseMiddleware']
    # Find security middleware index
    try:
        security_idx = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
        # Insert WhiteNoise right after security middleware
        MIDDLEWARE.insert(security_idx + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    except ValueError:
        # If security middleware not found, add WhiteNoise at the beginning
        MIDDLEWARE.insert(0, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Disable migrations for deployment speed (optional)
# MIGRATION_MODULES = {app: 'core.nomigrations' for app in INSTALLED_APPS} 