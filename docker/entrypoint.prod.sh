#!/bin/bash
set -e

echo "========================================"
echo "Family Wiki Production Environment"
echo "========================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
# Extract database connection details from DATABASE_URL
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')

echo "Connecting to database at ${DB_HOST}:${DB_PORT} as user ${DB_USER}"
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
    echo "PostgreSQL is unavailable - sleeping for 3 seconds..."
    sleep 3
done

echo "PostgreSQL is ready!"

# Initialize database tables if needed
echo "Initializing database tables..."
python -c "
from app import create_app
app = create_app()
app.app_context().push()
from web_app.database import db
try:
    # Run database migrations
    from flask_migrate import upgrade
    upgrade()
    print('Database migrations applied successfully!')
    
    # Load default prompts
    from web_app.services.prompt_service import prompt_service
    prompt_service.load_default_prompts()
    print('Default prompts loaded!')
except Exception as e:
    print(f'Database initialization error: {e}')
    exit(1)
"

echo "========================================"
echo "Starting Gunicorn production server..."
echo "Application will be available on port 5000"
echo "========================================"

# Start Gunicorn with production settings
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 2 \
    --worker-class gthread \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "app:app"