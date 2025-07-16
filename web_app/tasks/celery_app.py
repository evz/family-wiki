"""
Celery application configuration
"""
import os
from celery import Celery

def make_celery():
    """Create Celery instance"""
    broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    celery = Celery('family_wiki')
    celery.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    
    return celery

# Global celery instance
celery_app = make_celery()