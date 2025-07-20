"""
System status and tool execution API blueprint
"""


from flask import Blueprint, jsonify

from web_app.services.system_service import system_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

api_system = Blueprint('api_system', __name__, url_prefix='/api')


@api_system.route('/status')
def status():
    """API endpoint to check system status"""
    system_status = system_service.check_system_status()
    return jsonify({
        'success': True,
        **system_status
    })


@api_system.route('/status/refresh')
def refresh_status():
    """API endpoint to refresh system status (for testing)"""
    system_status = system_service.check_system_status()
    return jsonify({
        'success': True,
        **system_status
    })


