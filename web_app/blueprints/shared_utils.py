"""
Shared utilities for blueprints
"""
from celery.exceptions import OperationalError
from flask import flash
from kombu.exceptions import ConnectionError
from kombu.exceptions import OperationalError as KombuOperationalError

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


def safe_task_submit(task_func, task_name, *args, **kwargs):
    """Safely submit a Celery task with proper broker exception handling.

    Args:
        task_func: The task function to call (e.g., process_pdfs_ocr.delay)
        task_name: Human-readable task name for error messages
        *args, **kwargs: Arguments to pass to the task function

    Returns:
        Task object if successful, None if failed
    """
    try:
        return task_func(*args, **kwargs)
    except (OperationalError, KombuOperationalError, ConnectionError) as e:
        logger.error(f"Broker connection failed for {task_name} task: {e}")
        flash('Unable to connect to task queue - check that Redis and Celery worker are running', 'error')
        return None
    except OSError as e:
        logger.error(f"Network error submitting {task_name} task: {e}")
        flash('Network error - unable to reach task queue', 'error')
        return None
    except Exception as e:
        logger.error(f"Unexpected error submitting {task_name} task: {e}", exc_info=True)
        flash('An unexpected error occurred while starting the job', 'error')
        return None
