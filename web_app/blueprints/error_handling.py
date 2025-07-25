"""
Standardized error handling for blueprint operations
"""
from collections.abc import Callable
from functools import wraps
from typing import Any

from celery.exceptions import OperationalError
from flask import flash, redirect, url_for
from kombu.exceptions import ConnectionError
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy.exc import SQLAlchemyError

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class TaskSubmissionError(Exception):
    """Custom exception for task submission failures"""
    pass


class FileOperationError(Exception):
    """Custom exception for file operation failures"""
    pass


def safe_task_submit(task_func: Callable, task_name: str, *args, **kwargs) -> Any | None:
    """Safely submit a Celery task with comprehensive error handling.

    Args:
        task_func: The task function to call (e.g., process_pdfs_ocr.delay)
        task_name: Human-readable task name for error messages
        *args, **kwargs: Arguments to pass to the task function

    Returns:
        Task object if successful, None if failed
        
    Raises:
        TaskSubmissionError: For task submission failures
    """
    try:
        return task_func(*args, **kwargs)
    except (OperationalError, KombuOperationalError, ConnectionError) as e:
        logger.error(f"Broker connection failed for {task_name} task: {e}")
        raise TaskSubmissionError('Unable to connect to task queue - check that Redis and Celery worker are running')
    except OSError as e:
        logger.error(f"Network error submitting {task_name} task: {e}")
        raise TaskSubmissionError('Network error - unable to reach task queue')
    except Exception as e:
        logger.error(f"Unexpected error submitting {task_name} task: {e}", exc_info=True)
        raise TaskSubmissionError('An unexpected error occurred while starting the job')


def safe_file_operation(operation_func: Callable, operation_name: str, *args, **kwargs) -> Any:
    """Safely perform file operations with comprehensive error handling.

    Args:
        operation_func: The file operation function to call
        operation_name: Human-readable operation name for error messages
        *args, **kwargs: Arguments to pass to the operation function

    Returns:
        Result of the operation if successful
        
    Raises:
        FileOperationError: For file operation failures
    """
    try:
        return operation_func(*args, **kwargs)
    except OSError as e:
        logger.error(f"File system error during {operation_name}: {e}")
        raise FileOperationError('File system error - check disk space and permissions')
    except PermissionError as e:
        logger.error(f"Permission error during {operation_name}: {e}")
        raise FileOperationError('Permission denied - check file/directory permissions')
    except ValueError as e:
        logger.error(f"Invalid data during {operation_name}: {e}")
        raise FileOperationError('Invalid file data or format')
    except Exception as e:
        logger.error(f"Unexpected error during {operation_name}: {e}", exc_info=True)
        raise FileOperationError(f'An unexpected error occurred during {operation_name}')


def safe_database_operation(operation_func: Callable, operation_name: str, *args, **kwargs) -> Any:
    """Safely perform database operations with comprehensive error handling.

    Args:
        operation_func: The database operation function to call
        operation_name: Human-readable operation name for error messages
        *args, **kwargs: Arguments to pass to the operation function

    Returns:
        Result of the operation if successful
        
    Raises:
        SQLAlchemyError: For database operation failures (re-raised with context)
    """
    try:
        return operation_func(*args, **kwargs)
    except SQLAlchemyError as e:
        logger.error(f"Database error during {operation_name}: {e}")
        raise  # Re-raise SQLAlchemy errors with original type
    except Exception as e:
        logger.error(f"Unexpected error during {operation_name}: {e}", exc_info=True)
        raise


def handle_blueprint_errors(redirect_url: str = 'main.index'):
    """Decorator to handle common blueprint errors with consistent responses.
    
    Args:
        redirect_url: URL endpoint to redirect to on error
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TaskSubmissionError as e:
                flash(str(e), 'error')
                return redirect(url_for(redirect_url))
            except FileOperationError as e:
                flash(str(e), 'error')
                return redirect(url_for(redirect_url))
            except SQLAlchemyError as e:
                logger.error(f"Database error in {func.__name__}: {e}")
                flash('Database error occurred - please try again', 'error')
                return redirect(url_for(redirect_url))
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                flash('An unexpected error occurred - please try again', 'error')
                return redirect(url_for(redirect_url))
        return wrapper
    return decorator


def get_task_status_safely(task, task_id: str) -> dict:
    """Safely get task status with comprehensive error handling.
    
    Args:
        task: Celery task object
        task_id: Task ID for logging
        
    Returns:
        Dictionary with status information
    """
    try:
        state = task.state

        if state == 'PENDING':
            return {
                'status': 'pending',
                'message': 'Task is waiting to be processed',
                'progress': 0
            }
        elif state == 'PROGRESS':
            result = task.result or {}
            return {
                'status': 'running',
                'message': result.get('status', 'Task is running'),
                'progress': result.get('progress', 50)
            }
        elif state == 'SUCCESS':
            return {
                'status': 'completed',
                'message': 'Task completed successfully',
                'progress': 100,
                'result': task.result
            }
        elif state == 'FAILURE':
            error_msg = _format_task_error(task.result)
            return {
                'status': 'failed',
                'message': f'Task failed: {error_msg}',
                'progress': 0,
                'error': error_msg
            }
        else:
            return {
                'status': state.lower(),
                'message': f'Task status: {state}',
                'progress': 25
            }

    except ImportError as e:
        logger.error(f"Celery import error for task {task_id}: {e}")
        return {
            'status': 'error',
            'message': 'System configuration error - Celery not available',
            'progress': 0
        }
    except ConnectionError as e:
        logger.error(f"Redis connection error for task {task_id}: {e}")
        return {
            'status': 'error',
            'message': 'Unable to connect to task queue',
            'progress': 0
        }
    except AttributeError as e:
        logger.error(f"Invalid task object for {task_id}: {e}")
        return {
            'status': 'error',
            'message': 'Invalid task ID or task no longer exists',
            'progress': 0
        }
    except Exception as e:
        logger.error(f"Unexpected error getting status for task {task_id}: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': 'Unable to retrieve task status',
            'progress': 0
        }


def _format_task_error(error_result) -> str:
    """Format task error result into human-readable message."""
    if isinstance(error_result, dict):
        return error_result.get('error', 'Unknown error occurred')
    elif hasattr(error_result, 'args') and error_result.args:
        return str(error_result.args[0])
    else:
        error_str = str(error_result)
        return error_str if error_str else 'Task failed with unknown error'
