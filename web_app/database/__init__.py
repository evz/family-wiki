"""
Database configuration and models for Family Wiki
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()

def init_db():
    """Initialize database tables and load default data"""
    # Create all tables
    db.create_all()

    # Load default prompts (avoiding circular import by importing here)
    try:
        from web_app.services.prompt_service import prompt_service
        prompt_service.load_default_prompts()
    except Exception as e:
        print(f"Warning: Could not load default prompts: {e}")

def init_app(app):
    """Initialize database extensions with Flask app"""
    db.init_app(app)
    migrate.init_app(app, db)

    # Import all models to ensure they're registered with SQLAlchemy
    # This is especially important for testing where we use db.create_all()
    from web_app.database import models  # noqa: F401

    # Note: Database tables are now created via Flask-Migrate migrations
    # Default prompts are loaded in the Docker entrypoint scripts
