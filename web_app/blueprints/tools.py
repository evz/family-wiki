"""
Tools dashboard blueprint - unified job management
"""
import uuid

from celery.exceptions import OperationalError
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from kombu.exceptions import ConnectionError
from kombu.exceptions import OperationalError as KombuOperationalError

from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.extraction_tasks import extract_genealogy_data
from web_app.tasks.gedcom_tasks import generate_gedcom_file
from web_app.tasks.ocr_tasks import process_pdfs_ocr
from web_app.tasks.research_tasks import generate_research_questions


logger = get_project_logger(__name__)

tools_bp = Blueprint('tools', __name__, url_prefix='/tools')


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

@tools_bp.route('/')
def dashboard():
    """Unified tools dashboard with job table and input forms"""
    # Get job data - for now we'll return empty, but this could be expanded
    # to inspect Redis for all tasks
    jobs = []
    return render_template('tools/dashboard.html', jobs=jobs)

@tools_bp.route('/start-ocr', methods=['POST'])
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
        return redirect(url_for('tools.dashboard'))

    # Save uploaded files first
    try:
        saved_files = []
        for pdf_file in pdf_files:
            if pdf_file.filename != '':
                file_id = file_repo.save_uploaded_file(pdf_file, task_id, 'ocr', 'input')
                if file_id:
                    saved_files.append(file_id)
                else:
                    flash(f'Failed to save file: {pdf_file.filename}', 'error')

        if not saved_files:
            flash('No files were successfully uploaded', 'error')
            return redirect(url_for('tools.dashboard'))

        # Now start the task with the pre-generated task ID
        task = safe_task_submit(process_pdfs_ocr.apply_async, "OCR", task_id=task_id)
        if task:
            flash(f'OCR job started with {len(saved_files)} uploaded files. Task ID: {task.id}', 'success')
            logger.info(f"Started OCR task with uploaded files: {task.id}")

    except OSError as e:
        logger.error(f"File system error saving uploaded files: {e}")
        flash('Error saving uploaded files - check disk space and permissions', 'error')

    return redirect(url_for('tools.dashboard'))

@tools_bp.route('/start-extraction', methods=['POST'])
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
        return redirect(url_for('tools.dashboard'))

    # Save uploaded file first
    try:
        file_id = file_repo.save_uploaded_file(text_file, task_id, 'extraction', 'input')
        if not file_id:
            flash('Failed to save uploaded text file', 'error')
            return redirect(url_for('tools.dashboard'))

        # Start the task with the pre-generated task ID
        task = safe_task_submit(extract_genealogy_data.apply_async, "extraction", task_id=task_id)
        if task:
            flash(f'Extraction job started with uploaded file. Task ID: {task.id}', 'success')
            logger.info(f"Started extraction task with uploaded file: {task.id}")

    except OSError as e:
        logger.error(f"File system error saving uploaded extraction file: {e}")
        flash('Error saving uploaded file - check disk space and permissions', 'error')

    return redirect(url_for('tools.dashboard'))

@tools_bp.route('/start-gedcom', methods=['POST'])
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
        return redirect(url_for('tools.dashboard'))

    # Save uploaded file first
    try:
        file_id = file_repo.save_uploaded_file(input_file, task_id, 'gedcom', 'input')
        if not file_id:
            flash('Failed to save uploaded input file', 'error')
            return redirect(url_for('tools.dashboard'))

        # Start the task with the pre-generated task ID
        task = safe_task_submit(generate_gedcom_file.apply_async, "GEDCOM", task_id=task_id)
        if task:
            flash(f'GEDCOM generation job started with uploaded file. Task ID: {task.id}', 'success')
            logger.info(f"Started GEDCOM task with uploaded file: {task.id}")

    except OSError as e:
        logger.error(f"File system error saving uploaded GEDCOM file: {e}")
        flash('Error saving uploaded file - check disk space and permissions', 'error')

    return redirect(url_for('tools.dashboard'))

@tools_bp.route('/start-research', methods=['POST'])
def start_research():
    """Start research questions job from form"""
    input_file = request.files.get('input_file')
    file_repo = JobFileRepository()

    # Generate task ID first
    task_id = str(uuid.uuid4())

    # If no file uploaded, use latest extraction results
    if not input_file or input_file.filename == '':
        try:
            task = generate_research_questions.apply_async(task_id=task_id)
            flash(f'Research questions job started using latest extraction results. Task ID: {task.id}', 'success')
            logger.info(f"Started research task: {task.id}")
        except Exception as e:
            logger.error(f"Failed to start research task: {e}")
            flash(f'Failed to start research job: {str(e)}', 'error')

        return redirect(url_for('tools.dashboard'))

    # Save uploaded file first
    try:
        file_id = file_repo.save_uploaded_file(input_file, task_id, 'research', 'input')
        if not file_id:
            flash('Failed to save uploaded input file', 'error')
            return redirect(url_for('tools.dashboard'))

        # Start the task with the pre-generated task ID
        task = generate_research_questions.apply_async(task_id=task_id)

        flash(f'Research questions job started with uploaded file. Task ID: {task.id}', 'success')
        logger.info(f"Started research task with uploaded file: {task.id}")

    except Exception as e:
        logger.error(f"Failed to start research task: {e}")
        flash(f'Failed to start research job: {str(e)}', 'error')

    return redirect(url_for('tools.dashboard'))

@tools_bp.route('/api/jobs')
def api_jobs():
    """API endpoint to get all jobs for the table"""
    # This would need Redis inspection to get all tasks
    # For now, return empty - we'll build this incrementally
    return jsonify({'jobs': []})

@tools_bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_job(task_id):
    """Cancel a running job"""
    try:
        # Try both task types
        for task_func in [extract_genealogy_data, process_pdfs_ocr]:
            task = task_func.AsyncResult(task_id)
            if task.state in ['PENDING', 'RUNNING']:
                task.revoke(terminate=True)
                flash('Job cancelled successfully', 'success')
                return redirect(url_for('tools.dashboard'))

        flash('Job cannot be cancelled (not running)', 'error')
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        flash(f'Error cancelling job: {str(e)}', 'error')

    return redirect(url_for('tools.dashboard'))

@tools_bp.route('/download/<task_id>')
def download_result(task_id):
    """Download result file for completed job"""
    file_repo = JobFileRepository()

    try:
        # Get the download file from the repository
        download_file = file_repo.get_download_file(task_id, None)  # job_type not needed for now

        if not download_file:
            flash('No download available for this job', 'error')
            return redirect(url_for('tools.dashboard'))

        # Create a file-like object from the stored data
        from io import BytesIO
        file_data = BytesIO(download_file.file_data)

        return send_file(
            file_data,
            as_attachment=True,
            download_name=download_file.filename,
            mimetype=download_file.content_type
        )

    except OSError as e:
        logger.error(f"IO error downloading result for task {task_id}: {e}")
        flash('File system error occurred while preparing download', 'error')
    except ValueError as e:
        logger.error(f"Invalid data for task {task_id}: {e}")
        flash('Invalid file data - cannot create download', 'error')
    except ImportError as e:
        logger.error(f"Missing dependency for download: {e}")
        flash('System configuration error - missing required components', 'error')
    except Exception as e:
        logger.error(f"Unexpected error downloading result for task {task_id}: {e}", exc_info=True)
        flash('An unexpected error occurred while preparing the download', 'error')

    return redirect(url_for('tools.dashboard'))

@tools_bp.route('/research-questions/<task_id>')
def view_research_questions(task_id):
    """View research questions for a completed job"""
    try:
        # Get task result
        task = generate_research_questions.AsyncResult(task_id)

        if task.state == 'PENDING':
            flash('Research questions task is still pending', 'warning')
            return redirect(url_for('tools.dashboard'))

        if task.state == 'FAILURE':
            error_msg = str(task.result) if task.result else 'Unknown error'
            flash(f'Research questions task failed: {error_msg}', 'error')
            return redirect(url_for('tools.dashboard'))

        if task.state != 'SUCCESS':
            flash(f'Research questions task is still running (status: {task.state})', 'info')
            return redirect(url_for('tools.dashboard'))

        # Get the result data
        result = task.result
        if not result or not result.get('success'):
            flash('Research questions generation was not successful', 'error')
            return redirect(url_for('tools.dashboard'))

        questions = result.get('questions', [])
        input_file = result.get('input_file', 'Unknown')
        total_questions = result.get('total_questions', len(questions) if isinstance(questions, list) else 0)

        return render_template('tools/research_questions.html',
                             task_id=task_id,
                             questions=questions,
                             input_file=input_file,
                             total_questions=total_questions)

    except AttributeError as e:
        logger.error(f"Task object error for {task_id}: {e}")
        flash('Invalid task ID or task no longer exists', 'error')
    except KeyError as e:
        logger.error(f"Missing expected data in task result for {task_id}: {e}")
        flash('Task result is incomplete or corrupted', 'error')
    except Exception as e:
        logger.error(f"Unexpected error viewing research questions for task {task_id}: {e}", exc_info=True)
        flash('An unexpected error occurred while retrieving research questions', 'error')

    return redirect(url_for('tools.dashboard'))
