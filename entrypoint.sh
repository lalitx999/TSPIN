#!/bin/bash
set -e

echo "[TSPI Production] Checking PostgreSQL connection at ${DB_HOST:-db}:${DB_PORT:-5432}..."
while ! nc -z ${DB_HOST:-db} ${DB_PORT:-5432}; do
  sleep 0.5
done
echo "[TSPI Production] PostgreSQL is ready!"

# Apply migrations
echo "[TSPI Production] Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "[TSPI Production] Collecting static assets..."
python manage.py collectstatic --noinput

# Start Gunicorn server
echo "[TSPI Production] Starting Gunicorn WSGI server..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --worker-class gthread \
    --threads ${GUNICORN_THREADS:-8} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
