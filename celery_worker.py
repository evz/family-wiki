"""
Celery worker entry point

Start workers with: celery -A celery_worker.celery worker --loglevel=info
"""
from web_app import create_app
from web_app.tasks.celery_app import celery as celery_instance


# Create Flask app - environment variables provided by Docker/deployment
app = create_app()

# The Celery instance is already configured in web_app/__init__.py via init_celery()
# We just need to expose it as 'celery' for the worker command
celery = celery_instance
