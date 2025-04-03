#!/bin/sh

# Apply database migrations
echo "Applying database migrations..."
cd clean_backend
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start server
echo "Starting server..."
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 