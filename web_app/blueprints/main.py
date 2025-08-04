"""
Main blueprint for web interface
"""


from flask import Blueprint, render_template

from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.services.system_service import SystemService
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main dashboard showing available tools"""
    # Get system status for the UI
    system_service = SystemService()
    system_status = system_service.check_system_status()

    # Get database statistics
    repository = GenealogyDataRepository()
    db_stats = repository.get_database_stats()

    return render_template('index.html', system_status=system_status, db_stats=db_stats)



