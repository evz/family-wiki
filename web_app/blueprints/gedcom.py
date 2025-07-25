"""
GEDCOM generation blueprint - handles genealogy file format creation
"""
import uuid

from flask import Blueprint, flash, redirect, request, url_for

from web_app.blueprints.error_handling import (
    handle_blueprint_errors,
    safe_file_operation,
    safe_task_submit,
)
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.gedcom_tasks import generate_gedcom_file


logger = get_project_logger(__name__)

gedcom_bp = Blueprint('gedcom', __name__, url_prefix='/gedcom')


@gedcom_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_gedcom():
    """Start GEDCOM generation job from form"""
    input_file = request.files.get('input_file')
    file_repo = JobFileRepository()

    # Generate task ID first
    task_id = str(uuid.uuid4())

    # If no file uploaded, use latest extraction results
    if not input_file or input_file.filename == '':
        task = safe_task_submit(generate_gedcom_file.apply_async, "GEDCOM", task_id=task_id)
        if task:
            flash(f'GEDCOM generation job started using latest extraction results. Task ID: {task.id}', 'success')
            logger.info(f"Started GEDCOM task: {task.id}")
        return redirect(url_for('main.index'))

    # Save uploaded file first
    file_id = safe_file_operation(
        file_repo.save_uploaded_file,
        "GEDCOM input file upload",
        input_file, task_id, 'gedcom', 'input'
    )
    if not file_id:
        flash('Failed to save uploaded input file', 'error')
        return redirect(url_for('main.index'))

    # Start the task with the pre-generated task ID
    task = safe_task_submit(generate_gedcom_file.apply_async, "GEDCOM", task_id=task_id)
    flash(f'GEDCOM generation job started with uploaded file. Task ID: {task.id}', 'success')
    logger.info(f"Started GEDCOM task with uploaded file: {task.id}")

    return redirect(url_for('main.index'))
