#!/usr/bin/env python3
"""
Family Wiki Tools - Unified Flask application with CLI commands and web interface
"""

import os
from pathlib import Path

from flask import Flask

from web_app.blueprints.api import api
from web_app.blueprints.entities import entities
from web_app.blueprints.extraction import extraction
from web_app.blueprints.main import main
from web_app.blueprints.rag import rag
from web_app.commands import register_commands
from web_app.database import init_app as init_database
from web_app.shared.logging_config import get_project_logger


PROJECT_ROOT = Path(__file__).parent


class Config:
    """Configuration class for Flask app with environment variable support"""

    def __init__(self):
        # Flask configuration
        self.SECRET_KEY = os.environ.get('SECRET_KEY') or 'family-wiki-secret-key-change-in-production'

        # Database configuration
        self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///family_wiki.db'
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False

        # Ollama configuration
        self.OLLAMA_HOST = os.environ.get('OLLAMA_HOST') or '192.168.1.234'
        self.OLLAMA_PORT = int(os.environ.get('OLLAMA_PORT', '11434'))
        self.OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL') or 'aya:35b-23'

    @property
    def ollama_base_url(self):
        """Construct full Ollama URL"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"


def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    config_instance = config_class()
    app.config.from_object(config_instance)

    # Configure static files to use web_app/static
    app.static_folder = PROJECT_ROOT / 'web_app' / 'static'

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(entities)
    app.register_blueprint(rag)
    app.register_blueprint(extraction)

    # Initialize database
    init_database(app)

    # Register CLI commands
    register_commands(app)

    # Configure logging
    logger = get_project_logger(__name__)
    logger.info(f"Flask app created with Ollama at {config_instance.ollama_base_url} using model {config_instance.OLLAMA_MODEL}")
    logger.info(f"Database configured: {config_instance.SQLALCHEMY_DATABASE_URI}")

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
