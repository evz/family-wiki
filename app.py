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
# Temporarily disabled for Phase 2 testing - has GEDCOM dependencies
# from web_app.blueprints.tools import tools_bp
from web_app.database import init_app as init_database
from web_app.error_handlers import register_error_handlers


PROJECT_ROOT = Path(__file__).parent


class Config:
    """Configuration class for Flask app with required environment variables"""

    def __init__(self):
        # Flask configuration
        self.secret_key = self._require_env('SECRET_KEY')

        # Database configuration
        self.sqlalchemy_database_uri = self._require_env('DATABASE_URL')
        self.sqlalchemy_track_modifications = False

        # Celery configuration
        self.celery_broker_url = self._require_env('CELERY_BROKER_URL')
        self.celery_result_backend = self._require_env('CELERY_RESULT_BACKEND')

        # Ollama configuration
        self.ollama_host = self._require_env('OLLAMA_HOST')
        self.ollama_port = int(self._require_env('OLLAMA_PORT'))
        self.ollama_model = self._require_env('OLLAMA_MODEL')

    def _require_env(self, var_name: str) -> str:
        """Require environment variable or raise error"""
        value = os.environ.get(var_name)
        if not value:
            raise RuntimeError(f"Required environment variable {var_name} is not set")
        return value

    @property
    def ollama_base_url(self) -> str:
        """Construct full Ollama URL"""
        return f"http://{self.ollama_host}:{self.ollama_port}"


def create_app(config=None):
    """Application factory"""
    app = Flask(__name__)

    # Initialize configuration
    if config is None:
        config = Config()

    # Set Flask config from our config object
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.sqlalchemy_database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.sqlalchemy_track_modifications
    app.config['CELERY_BROKER_URL'] = config.celery_broker_url
    app.config['CELERY_RESULT_BACKEND'] = config.celery_result_backend
    app.config['OLLAMA_HOST'] = config.ollama_host
    app.config['OLLAMA_PORT'] = config.ollama_port
    app.config['OLLAMA_MODEL'] = config.ollama_model

    # Configure Celery app context
    from web_app.tasks.celery_app import celery_app
    celery_app.conf.update(app.config)

    # Configure static files to use web_app/static
    app.static_folder = PROJECT_ROOT / 'web_app' / 'static'

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(prompts_bp)
    # app.register_blueprint(tools_bp)  # Temporarily disabled
    app.register_blueprint(entities)
    app.register_blueprint(rag)

    # Initialize database
    init_database(app)

    # Register error handlers
    register_error_handlers(app)

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
