#!/usr/bin/env python3
"""
Family Wiki Tools - Unified Flask application with CLI commands and web interface
"""

import os
from pathlib import Path

from flask import Flask

from web_app.blueprints.entities import entities
from web_app.blueprints.main import main
from web_app.blueprints.prompts import prompts_bp
from web_app.blueprints.rag import rag
from web_app.blueprints.tools import tools_bp
from web_app.database import init_app as init_database
from web_app.error_handlers import register_error_handlers
from web_app.shared.logging_config import get_project_logger


PROJECT_ROOT = Path(__file__).parent


class Config:
    """Configuration class for Flask app with environment variable support"""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'family-wiki-secret-key-change-in-production'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://family_wiki_user:family_wiki_password@localhost:5432/family_wiki'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'

    # Ollama configuration
    OLLAMA_HOST = os.environ.get('OLLAMA_HOST') or 'localhost'
    OLLAMA_PORT = int(os.environ.get('OLLAMA_PORT', '11434'))
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL') or 'qwen2.5:7b'

    @property
    def ollama_base_url(self):
        """Construct full Ollama URL"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"


def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure Celery app context
    from web_app.tasks.celery_app import celery_app
    celery_app.conf.update(app.config)

    # Configure static files to use web_app/static
    app.static_folder = PROJECT_ROOT / 'web_app' / 'static'

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(prompts_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(entities)
    app.register_blueprint(rag)

    # Initialize database
    init_database(app)


    # Register error handlers
    register_error_handlers(app)

    # Configure logging
    logger = get_project_logger(__name__)
    logger.info(f"Flask app created with Ollama at http://{app.config['OLLAMA_HOST']}:{app.config['OLLAMA_PORT']} using model {app.config['OLLAMA_MODEL']}")
    logger.info(f"Database configured: {app.config['SQLALCHEMY_DATABASE_URI']}")

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
