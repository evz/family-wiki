"""
Extraction blueprint for LLM extraction API endpoints
"""


from flask import Blueprint, jsonify, request

from web_app.services.extraction_service import extraction_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

extraction = Blueprint('extraction', __name__, url_prefix='/api/extraction')

@extraction.route('/start')
def start_extraction():
    """Start a new extraction task"""
    try:
        text_file = request.args.get('text_file')  # Optional custom text file

        task_id = extraction_service.start_extraction(
            text_file=text_file,
            progress_callback=None  # Could add WebSocket support later
        )

        logger.info(f"Started extraction task: {task_id}")

        return jsonify({
            'task_id': task_id,
            'status': 'started',
            'message': 'Extraction task started successfully'
        })

    except Exception as e:
        logger.error(f"Failed to start extraction: {e}")
        return jsonify({
            'error': f'Failed to start extraction: {str(e)}'
        }), 500

@extraction.route('/status/<task_id>')
def get_task_status(task_id):
    """Get the status of an extraction task"""
    try:
        status = extraction_service.get_task_status(task_id)

        if not status:
            return jsonify({'error': 'Task not found'}), 404

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting task status {task_id}: {e}")
        return jsonify({
            'error': f'Error getting task status: {str(e)}'
        }), 500

@extraction.route('/tasks')
def list_tasks():
    """List all active extraction tasks"""
    try:
        tasks = []
        for task_id, task in extraction_service.tasks.items():
            tasks.append({
                'id': task_id,
                'status': task.status,
                'progress': task.progress,
                'start_time': task.start_time.isoformat() if task.start_time else None
            })

        return jsonify({
            'tasks': tasks,
            'total': len(tasks)
        })

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({
            'error': f'Error listing tasks: {str(e)}'
        }), 500

@extraction.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running extraction task"""
    try:
        task = extraction_service.get_task(task_id)

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task.status not in ['pending', 'running']:
            return jsonify({'error': 'Task cannot be cancelled'}), 400

        # Note: In a real implementation, we'd need a way to stop the thread
        # For now, we'll just mark it as failed
        task.status = 'cancelled'
        task.error = 'Task cancelled by user'

        logger.info(f"Cancelled extraction task: {task_id}")

        return jsonify({
            'message': 'Task cancelled successfully',
            'task_id': task_id
        })

    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({
            'error': f'Error cancelling task: {str(e)}'
        }), 500

@extraction.route('/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """Clean up old completed/failed tasks"""
    try:
        max_age_hours = request.json.get('max_age_hours', 24) if request.json else 24

        extraction_service.cleanup_old_tasks(max_age_hours)

        return jsonify({
            'message': f'Cleaned up tasks older than {max_age_hours} hours'
        })

    except Exception as e:
        logger.error(f"Error cleaning up tasks: {e}")
        return jsonify({
            'error': f'Error cleaning up tasks: {str(e)}'
        }), 500
