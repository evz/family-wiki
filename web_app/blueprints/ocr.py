"""
OCR processing blueprint - handles PDF OCR operations
"""
import uuid

from flask import Blueprint, flash, redirect, request, url_for

from web_app.database import db
from web_app.blueprints.blueprint_utils import (
    handle_blueprint_errors,
    safe_file_operation,
    safe_task_submit,
)
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.ocr_tasks import process_pdfs_ocr


logger = get_project_logger(__name__)

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')


@ocr_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_ocr():
    """Start OCR job from form"""
    pdf_files = request.files.getlist('pdf_files')
    file_repo = JobFileRepository()

    # Generate task ID first
    task_id = str(uuid.uuid4())

    # If no files uploaded, use default folder
    if not pdf_files or all(f.filename == '' for f in pdf_files):
        task = safe_task_submit(process_pdfs_ocr.delay, "OCR")
        if task:
            flash(f'OCR job started using default folder. Task ID: {task.id}', 'success')
            logger.info(f"Started OCR task: {task.id}")
        return redirect(url_for('main.index'))

    # Save uploaded files first with transaction management
    saved_files = []
    with db.session.begin():
        for pdf_file in pdf_files:
            if pdf_file.filename != '':
                file_id = safe_file_operation(
                    file_repo.save_uploaded_file,
                    "file upload",
                    pdf_file, task_id, 'ocr', 'input'
                )
                if file_id:
                    saved_files.append(file_id)
                else:
                    flash(f'Failed to save file: {pdf_file.filename}', 'error')

    if not saved_files:
        flash('No files were successfully uploaded', 'error')
        return redirect(url_for('main.index'))

    # Now start the task with the pre-generated task ID
    task = safe_task_submit(process_pdfs_ocr.apply_async, "OCR", task_id=task_id)
    flash(f'OCR job started with {len(saved_files)} uploaded files. Task ID: {task.id}', 'success')
    logger.info(f"Started OCR task with uploaded files: {task.id}")

    return redirect(url_for('main.index'))
