"""
Extraction blueprint for LLM extraction API endpoints
"""


from flask import Blueprint, jsonify, request

from web_app.tasks.extraction_tasks import extract_genealogy_data
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

extraction = Blueprint('extraction', __name__, url_prefix='/api/extraction')

@extraction.route('/start')
def start_extraction():
    """Start a new extraction task"""
    try:
        text_file = request.args.get('text_file')  # Optional custom text file

        task = extract_genealogy_data.delay(text_file)
        task_id = task.id

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
        task = extract_genealogy_data.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            # Task not found or not started yet
            return jsonify({'error': 'Task not found'}), 404
        elif task.state == 'RUNNING':
            # Task is running, return progress info
            return jsonify({
                'status': task.state,
                'meta': task.info
            })
        elif task.state == 'SUCCESS':
            # Task completed successfully
            return jsonify({
                'status': task.state,
                'result': task.result
            })
        elif task.state == 'FAILURE':
            # Task failed
            return jsonify({
                'status': task.state,
                'error': str(task.info)
            })
        else:
            # Unknown state
            return jsonify({
                'status': task.state,
                'meta': task.info if hasattr(task, 'info') else None
            })

    except Exception as e:
        logger.error(f"Error getting task status {task_id}: {e}")
        return jsonify({
            'error': f'Error getting task status: {str(e)}'
        }), 500

@extraction.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running extraction task"""
    try:
        task = extract_genealogy_data.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            return jsonify({'error': 'Task not found'}), 404
        
        if task.state not in ['PENDING', 'RUNNING']:
            return jsonify({'error': 'Task cannot be cancelled'}), 400
        
        # Revoke the task
        task.revoke(terminate=True)
        
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
