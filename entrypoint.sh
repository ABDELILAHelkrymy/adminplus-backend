#!/bin/sh
# =============================================================================
# entrypoint.sh — Automated bootstrap for comptago backend container
# Runs on every `docker-compose up`. Safe to run repeatedly (idempotent).
# =============================================================================

set -e  # Exit immediately if any command fails

echo "======================================"
echo "  Comptago Backend — Docker Startup"
echo "======================================"

# Move into the Django src directory
cd /app/src

echo ""
echo ">>> [1/4] Waiting for PostgreSQL to be ready..."
# Loop until pg_isready succeeds (avoids race conditions on first docker-compose up)
until python -c "
import sys, os
import psycopg2
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('ERROR: DATABASE_URL is not set!', file=sys.stderr)
    sys.exit(1)

parsed = urlparse(db_url)
try:
    conn = psycopg2.connect(
        dbname=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        connect_timeout=3
    )
    conn.close()
    print('PostgreSQL is ready.')
except psycopg2.OperationalError as e:
    print(f'Not ready yet: {e}', file=sys.stderr)
    sys.exit(1)
"; do
    echo "  PostgreSQL not ready — retrying in 2s..."
    sleep 2
done

echo ""
echo ">>> [2/4] Running database migrations..."
python manage.py migrate --noinput

echo ""
echo ">>> [3/4] Seeding roles and permissions (idempotent — safe to run repeatedly)..."
# Uses the comprehensive command (setup_permissions_roles) which does get_or_create
# so it will never duplicate data if roles/permissions already exist.
python manage.py setup_permissions_roles

echo ""
echo ">>> [4/4] Starting Django development server..."
echo "======================================"
exec python manage.py runserver 0.0.0.0:8000
