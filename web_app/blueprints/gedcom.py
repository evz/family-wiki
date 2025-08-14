"""
GEDCOM generation blueprint - handles genealogy file format creation
"""
from flask import Blueprint, flash, redirect, request, url_for

from web_app.blueprints.blueprint_utils import handle_blueprint_errors
from web_app.services.gedcom_job_service import GedcomJobService
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

gedcom_bp = Blueprint('gedcom', __name__, url_prefix='/gedcom')


@gedcom_bp.route('/start', methods=['POST'])
@handle_blueprint_errors()
def start_gedcom():
    """Start GEDCOM generation job from form"""
    input_file = request.files.get('input_file')
    input_files = [input_file] if input_file else []
    
    # Use service to handle business logic
    service = GedcomJobService()
    result = service.start_gedcom_job(input_files)
    
    if result.success:
        flash(result.message, 'success')
        logger.info(f"Started GEDCOM task: {result.task_id}")
    else:
        flash(f'Failed to start GEDCOM job: {result.error}', 'error')
        logger.error(f"GEDCOM job failed: {result.error}")

    return redirect(url_for('main.index'))
