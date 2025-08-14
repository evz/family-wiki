"""
OCR processing blueprint - handles PDF OCR operations
"""
from flask import Blueprint, flash, redirect, request, url_for

from web_app.blueprints.blueprint_utils import handle_blueprint_errors
from web_app.database import db
from web_app.services.ocr_service import OCRService
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')


@ocr_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_ocr():
    """Start OCR job from form"""
    pdf_files = request.files.getlist('pdf_files')
    ocr_service = OCRService()

    # Service handles business logic, repositories handle data operations
    result = ocr_service.start_ocr_job(pdf_files)

    # Handle result
    if result.success:
        flash(result.message, 'success')
        logger.info(f"OCR job started successfully: {result.task_id}")
    else:
        flash(f'Failed to start OCR job: {result.error}', 'error')
        logger.error(f"OCR job failed: {result.error}")

    return redirect(url_for('main.index'))
