"""
Jobs management blueprint - handles job status, cancellation, and downloads
"""
from io import BytesIO

import amqp.exceptions
from celery import current_app as celery_app
from flask import Blueprint, flash, jsonify, redirect, send_file, url_for
from kombu.exceptions import ConnectionError

from web_app.blueprints.blueprint_utils import (
    handle_blueprint_errors,
    safe_file_operation,
)
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.extraction_tasks import extract_genealogy_data
from web_app.tasks.ocr_tasks import process_pdfs_ocr


logger = get_project_logger(__name__)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs_bp.route('/api/jobs')
def api_jobs():
    """API endpoint to get all jobs for the table"""
    # This would need Redis inspection to get all tasks
    # For now, return empty - we'll build this incrementally
    return jsonify({'jobs': []})


@jobs_bp.route('/api/jobs/<task_id>/status')
def api_job_status(task_id):
    """Get status of a specific task by querying Redis directly"""
    try:
        # Get task status directly from Celery backend (Redis)
        task_result = celery_app.AsyncResult(task_id)

        # Determine task type from task name
        task_type = _extract_task_type(task_result)

        # Build base response
        response = {
            'task_id': task_id,
            'status': task_result.state.lower(),
            'task_type': task_type
        }

        # Add state-specific information
        if task_result.state == 'PENDING':
            response.update({
                'message': 'Task is waiting to be processed',
                'progress': 0
            })

        elif task_result.state == 'RUNNING':
            progress, message = _extract_running_info(task_result)
            response.update({
                'progress': progress,
                'message': message
            })

        elif task_result.state == 'SUCCESS':
            response.update({
                'progress': 100,
                'message': 'Task completed successfully'
            })
            # Add success flag and download availability if available
            if task_result.result and isinstance(task_result.result, dict):
                response['success'] = task_result.result.get('success', True)
                response['download_available'] = task_result.result.get('download_available', False)

        elif task_result.state == 'FAILURE':
            error_message = _extract_failure_message(task_result)
            response.update({
                'progress': 0,
                'message': error_message,
                'error': error_message
            })

        elif task_result.state == 'RETRY':
            progress, message = _extract_retry_info(task_result)
            response.update({
                'progress': progress,
                'message': message
            })

        else:
            response.update({
                'message': f'Task state: {task_result.state}',
                'progress': 0
            })

        return jsonify(response)

    except ImportError as e:
        logger.error(f"Celery import error for task {task_id}: {e}")
        return _error_response(task_id, 'Celery not available', 503)
    except (ConnectionError, amqp.exceptions.ConnectionError) as e:
        logger.error(f"Redis connection error for task {task_id}: {e}")
        return _error_response(task_id, 'Unable to connect to task queue', 503)
    except AttributeError as e:
        logger.error(f"Invalid task ID {task_id}: {e}")
        return _error_response(task_id, 'Invalid task ID format', 400)
    except Exception as e:
        logger.error(f"Unexpected error getting status for task {task_id}: {e}", exc_info=True)
        return _error_response(task_id, 'Unable to retrieve task status', 500)


@jobs_bp.route('/cancel/<task_id>', methods=['POST'])
@handle_blueprint_errors()
def cancel_job(task_id):
    """Cancel a running job"""
    # Try both task types
    for task_func in [extract_genealogy_data, process_pdfs_ocr]:
        task = task_func.AsyncResult(task_id)
        if task.state in ['PENDING', 'RUNNING']:
            task.revoke(terminate=True)
            flash('Job cancelled successfully', 'success')
            return redirect(url_for('main.index'))

    flash('Job cannot be cancelled (not running)', 'error')
    return redirect(url_for('main.index'))


@jobs_bp.route('/download/<task_id>')
@handle_blueprint_errors()
def download_result(task_id):
    """Download result file for completed job"""
    file_repo = JobFileRepository()

    # Get the download file from the repository
    download_file = safe_file_operation(
        file_repo.get_download_file,
        "download file retrieval",
        task_id, None  # job_type not needed for now
    )

    if not download_file:
        flash('No download available for this job', 'error')
        return redirect(url_for('main.index'))

    # Create a file-like object from the stored data
    file_data = safe_file_operation(
        BytesIO,
        "file data preparation",
        download_file.file_data
    )

    return send_file(
        file_data,
        as_attachment=True,
        download_name=download_file.filename,
        mimetype=download_file.content_type
    )


def _extract_task_type(task_result):
    """Extract task type from task name"""
    task_name = getattr(task_result, 'name', None)
    if not task_name:
        return 'unknown'

    # Extract task type from full task name
    if 'ocr_tasks' in task_name:
        return 'ocr'
    elif 'extraction_tasks' in task_name:
        return 'extraction'
    elif 'gedcom_tasks' in task_name:
        return 'gedcom'
    elif 'research_tasks' in task_name:
        return 'research'
    else:
        return 'unknown'


def _extract_running_info(task_result):
    """Extract progress and message from running task"""
    if task_result.info:
        progress = task_result.info.get('progress', 50)
        message = task_result.info.get('status', 'Task is running')
        return progress, message
    else:
        return 50, 'Task is running'


def _extract_failure_message(task_result):
    """Extract clear error message from failed task"""
    if not task_result.result:
        return 'Task failed with unknown error'

    error_result = task_result.result

    # Handle different error result formats
    if isinstance(error_result, dict):
        # Check for structured error info
        if 'error' in error_result:
            return str(error_result['error'])
        elif 'message' in error_result:
            return str(error_result['message'])
        else:
            return 'Task failed with unknown error'
    else:
        # Handle exception objects or string errors
        error_str = str(error_result)
        return error_str if error_str else 'Task failed with unknown error'


def _extract_retry_info(task_result):
    """Extract progress and message from retrying task"""
    if task_result.info:
        progress = task_result.info.get('progress', 25)
        message = task_result.info.get('status', 'Task is being retried')
        return progress, message
    else:
        return 25, 'Task is being retried'


def _error_response(task_id, message, status_code=500):
    """Create standardized error response"""
    return jsonify({
        'task_id': task_id,
        'status': 'error',
        'message': message,
        'error': message
    }), status_code
