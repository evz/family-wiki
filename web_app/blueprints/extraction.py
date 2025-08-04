"""
Genealogy extraction blueprint - handles LLM-powered data extraction
"""
import uuid

from flask import Blueprint, flash, redirect, request, url_for

from web_app.blueprints.blueprint_utils import (
    handle_blueprint_errors,
    safe_file_operation,
    safe_task_submit,
)
from web_app.database import db
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.extraction_tasks import extract_genealogy_data


logger = get_project_logger(__name__)

extraction_bp = Blueprint('extraction', __name__, url_prefix='/extraction')


@extraction_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_extraction():
    """Start extraction job from form"""
    text_file = request.files.get('text_file')
    file_repo = JobFileRepository()

    # Generate task ID first
    task_id = str(uuid.uuid4())

    # If no file uploaded, use latest OCR results
    if not text_file or text_file.filename == '':
        task = safe_task_submit(extract_genealogy_data.apply_async, "extraction", task_id=task_id)
        if task:
            flash(f'Extraction job started using latest OCR results. Task ID: {task.id}', 'success')
            logger.info(f"Started extraction task: {task.id}")
        return redirect(url_for('main.index'))

    # Save uploaded file first with transaction management
    with db.session.begin():
        file_id = safe_file_operation(
            file_repo.save_uploaded_file,
            "text file upload",
            text_file, task_id, 'extraction', 'input'
        )
        if not file_id:
            flash('Failed to save uploaded text file', 'error')
            return redirect(url_for('main.index'))

    # Start the task with the pre-generated task ID
    task = safe_task_submit(extract_genealogy_data.apply_async, "extraction", task_id=task_id)
    flash(f'Extraction job started with uploaded file. Task ID: {task.id}', 'success')
    logger.info(f"Started extraction task with uploaded file: {task.id}")

    return redirect(url_for('main.index'))
