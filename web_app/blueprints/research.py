"""
Research questions blueprint - handles genealogy research question generation
"""
import uuid

from flask import Blueprint, flash, redirect, render_template, request, url_for

from web_app.blueprints.error_handling import (
    get_task_status_safely,
    handle_blueprint_errors,
    safe_file_operation,
    safe_task_submit,
)
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.research_tasks import generate_research_questions


logger = get_project_logger(__name__)

research_bp = Blueprint('research', __name__, url_prefix='/research')


@research_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_research():
    """Start research questions job from form"""
    input_file = request.files.get('input_file')
    file_repo = JobFileRepository()

    # Generate task ID first
    task_id = str(uuid.uuid4())

    # If no file uploaded, use latest extraction results
    if not input_file or input_file.filename == '':
        task = safe_task_submit(
            lambda: generate_research_questions.apply_async(task_id=task_id),
            "research questions"
        )
        flash(f'Research questions job started using latest extraction results. Task ID: {task.id}', 'success')
        logger.info(f"Started research task: {task.id}")
        return redirect(url_for('main.index'))

    # Save uploaded file first
    file_id = safe_file_operation(
        file_repo.save_uploaded_file,
        "research input file upload",
        input_file, task_id, 'research', 'input'
    )
    if not file_id:
        flash('Failed to save uploaded input file', 'error')
        return redirect(url_for('main.index'))

    # Start the task with the pre-generated task ID
    task = safe_task_submit(
        lambda: generate_research_questions.apply_async(task_id=task_id),
        "research questions"
    )
    flash(f'Research questions job started with uploaded file. Task ID: {task.id}', 'success')
    logger.info(f"Started research task with uploaded file: {task.id}")

    return redirect(url_for('main.index'))


@research_bp.route('/questions/<task_id>')
@handle_blueprint_errors()
def view_research_questions(task_id):
    """View research questions for a completed job"""
    # Get task result using safe status checking
    task = generate_research_questions.AsyncResult(task_id)
    status_info = get_task_status_safely(task, task_id)

    if status_info['status'] == 'pending':
        flash('Research questions task is still pending', 'warning')
        return redirect(url_for('main.index'))

    if status_info['status'] == 'failed':
        flash(f'Research questions task failed: {status_info["error"]}', 'error')
        return redirect(url_for('main.index'))

    if status_info['status'] != 'completed':
        flash(f'Research questions task is still running (status: {status_info["status"]})', 'info')
        return redirect(url_for('main.index'))

    # Get the result data
    result = status_info.get('result')
    if not result or not result.get('success'):
        flash('Research questions generation was not successful', 'error')
        return redirect(url_for('main.index'))

    questions = result.get('questions', [])
    input_file = result.get('input_file', 'Unknown')
    total_questions = result.get('total_questions', len(questions) if isinstance(questions, list) else 0)

    return render_template('tools/research_questions.html',
                         task_id=task_id,
                         questions=questions,
                         input_file=input_file,
                         total_questions=total_questions)
