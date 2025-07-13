#!/usr/bin/env python3
"""
Family Wiki Tools - Unified Flask application with CLI commands and web interface
"""

import sys
from pathlib import Path
from flask import Flask

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared_genealogy.logging_config import get_project_logger
from web_app.blueprints.main import main
from web_app.blueprints.extraction import extraction
from web_app.commands import register_commands

def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.secret_key = 'family-wiki-secret-key-change-in-production'
    
    # Configure static files to use web_app/static
    app.static_folder = PROJECT_ROOT / 'web_app' / 'static'
    
    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(extraction)
    
    # Register CLI commands
    register_commands(app)
    
    # Configure logging
    logger = get_project_logger(__name__)
    logger.info("Flask app created with blueprints and CLI commands")
    
    return app

def main_cli():
    """CLI entry point"""
    app = create_app()
    
    print("Family Wiki Tools - New Web Interface")
    print("=" * 50)
    print("Starting Flask server with improved architecture:")
    print("- Blueprint-based organization")
    print("- Shared service classes")
    print("- Proper progress tracking for LLM extraction")
    print("- Separated templates and static files")
    print()
    print("Access the interface at: http://localhost:5000")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main_cli()