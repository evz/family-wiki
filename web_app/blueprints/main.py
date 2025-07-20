"""
Main blueprint for web interface
"""


from flask import Blueprint, flash, redirect, render_template, url_for

from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.services.system_service import system_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main dashboard showing available tools"""
    # Get system status for the UI
    system_status = system_service.check_system_status()

    # Get database statistics
    repository = GenealogyDataRepository()
    db_stats = repository.get_database_stats()

    return render_template('index.html', system_status=system_status, db_stats=db_stats)

@main.route('/tools/<tool>')
def tool_page(tool):
    """Individual tool pages"""
    valid_tools = {
        'ocr': 'OCR Processing',
        'benchmark': 'Model Benchmarking',
        'extract': 'LLM Extraction',
        'gedcom': 'GEDCOM Generation',
        'research': 'Research Questions',
        'pipeline': 'Full Pipeline',
        'prompts': 'Prompt Management'
    }

    if tool not in valid_tools:
        flash(f'Unknown tool: {tool}', 'error')
        return redirect(url_for('main.index'))

    # Special handling for prompts tool
    if tool == 'prompts':
        return redirect(url_for('prompts.list_prompts'))

    # Redirect other tools to the new unified dashboard
    return redirect(url_for('tools.dashboard'))


