"""
Tools dashboard blueprint - unified job management
"""
import uuid

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for

from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.extraction_tasks import extract_genealogy_data
from web_app.tasks.gedcom_tasks import generate_gedcom_file
from web_app.tasks.ocr_tasks import process_pdfs_ocr
from web_app.tasks.research_tasks import generate_research_questions


logger = get_project_logger(__name__)

tools_bp = Blueprint('tools', __name__, url_prefix='/tools')

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
        try:
            task = process_pdfs_ocr.delay()
            flash(f'OCR job started using default folder. Task ID: {task.id}', 'success')
            logger.info(f"Started OCR task: {task.id}")
        except Exception as e:
            logger.error(f"Failed to start OCR task: {e}")
            flash(f'Failed to start OCR job: {str(e)}', 'error')

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
        task = process_pdfs_ocr.apply_async(task_id=task_id)

        flash(f'OCR job started with {len(saved_files)} uploaded files. Task ID: {task.id}', 'success')
        logger.info(f"Started OCR task with uploaded files: {task.id}")

    except Exception as e:
        logger.error(f"Failed to start OCR task: {e}")
        flash(f'Failed to start OCR job: {str(e)}', 'error')

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
        try:
            task = extract_genealogy_data.apply_async(task_id=task_id)
            flash(f'Extraction job started using latest OCR results. Task ID: {task.id}', 'success')
            logger.info(f"Started extraction task: {task.id}")
        except Exception as e:
            logger.error(f"Failed to start extraction task: {e}")
            flash(f'Failed to start extraction job: {str(e)}', 'error')

        return redirect(url_for('tools.dashboard'))

    # Save uploaded file first
    try:
        file_id = file_repo.save_uploaded_file(text_file, task_id, 'extraction', 'input')
        if not file_id:
            flash('Failed to save uploaded text file', 'error')
            return redirect(url_for('tools.dashboard'))

        # Start the task with the pre-generated task ID
        task = extract_genealogy_data.apply_async(task_id=task_id)

        flash(f'Extraction job started with uploaded file. Task ID: {task.id}', 'success')
        logger.info(f"Started extraction task with uploaded file: {task.id}")

    except Exception as e:
        logger.error(f"Failed to start extraction task: {e}")
        flash(f'Failed to start extraction job: {str(e)}', 'error')

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
        try:
            task = generate_gedcom_file.apply_async(task_id=task_id)
            flash(f'GEDCOM generation job started using latest extraction results. Task ID: {task.id}', 'success')
            logger.info(f"Started GEDCOM task: {task.id}")
        except Exception as e:
            logger.error(f"Failed to start GEDCOM task: {e}")
            flash(f'Failed to start GEDCOM job: {str(e)}', 'error')

        return redirect(url_for('tools.dashboard'))

    # Save uploaded file first
    try:
        file_id = file_repo.save_uploaded_file(input_file, task_id, 'gedcom', 'input')
        if not file_id:
            flash('Failed to save uploaded input file', 'error')
            return redirect(url_for('tools.dashboard'))

        # Start the task with the pre-generated task ID
        task = generate_gedcom_file.apply_async(task_id=task_id)

        flash(f'GEDCOM generation job started with uploaded file. Task ID: {task.id}', 'success')
        logger.info(f"Started GEDCOM task with uploaded file: {task.id}")

    except Exception as e:
        logger.error(f"Failed to start GEDCOM task: {e}")
        flash(f'Failed to start GEDCOM job: {str(e)}', 'error')

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

    except Exception as e:
        logger.error(f"Error downloading result for task {task_id}: {e}")
        flash(f'Error downloading result: {str(e)}', 'error')

    return redirect(url_for('tools.dashboard'))
