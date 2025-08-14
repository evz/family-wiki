"""
Genealogy extraction blueprint - handles LLM-powered data extraction
"""
from flask import Blueprint, flash, redirect, request, url_for

from web_app.blueprints.blueprint_utils import handle_blueprint_errors
from web_app.services.extraction_service import ExtractionService
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

extraction_bp = Blueprint('extraction', __name__, url_prefix='/extraction')


@extraction_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_extraction():
    """Start extraction job from form"""
    text_file = request.files.get('text_file')
    text_files = [text_file] if text_file else []
    
    # Use service to handle business logic
    service = ExtractionService()
    result = service.start_extraction_job(text_files)
    
    if result.success:
        flash(result.message, 'success')
        logger.info(f"Started extraction task: {result.task_id}")
    else:
        flash(f'Failed to start extraction job: {result.error}', 'error')
        logger.error(f"Extraction job failed: {result.error}")

    return redirect(url_for('main.index'))
