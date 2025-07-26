#!/bin/bash
# Database initialization script
set -e

echo "Initializing Family Wiki database..."

# Function to initialize database tables
init_database() {
    python -c "
import sys
import traceback
from web_app import create_app

try:
    print('Creating Flask application...')
    app = create_app()
    
    print('Setting up application context...')
    with app.app_context():
        from web_app.database import db
        
        print('Creating database tables...')
        db.create_all()
        
        print('Database initialization completed successfully!')
        
        # Optional: Add any initial data here
        # from web_app.services.prompt_service import prompt_service
        # prompt_service.ensure_default_prompts()
        
except Exception as e:
    print(f'Database initialization failed: {e}', file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
"
}

# Run initialization
init_database

echo "Database initialization script completed."