#!/bin/bash
set -e

echo "========================================"
echo "Family Wiki Development Environment"
echo "========================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
# Extract database connection details from DATABASE_URL
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')

echo "Connecting to database at ${DB_HOST}:${DB_PORT} as user ${DB_USER}"
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
    echo "PostgreSQL is unavailable - sleeping for 2 seconds..."
    sleep 2
done

echo "PostgreSQL is ready!"

# Initialize database tables if needed
echo "Initializing database tables..."
python -c "
from web_app import create_app
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
echo "Starting Flask development server..."
echo "Application will be available at http://localhost:5000"
echo "========================================"

# Start Flask in debug mode with hot reload
exec flask --app web_app run --host=0.0.0.0 --debug
