"""
Shared error handlers for Flask application and blueprints
"""

from flask import jsonify, render_template, request

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


def register_error_handlers(app_or_blueprint):
    """Register error handlers for Flask app or blueprint"""

    @app_or_blueprint.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        logger.warning(f"404 error: {request.url}")

        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Resource not found'}), 404

        return render_template('errors/404.html'), 404

    @app_or_blueprint.errorhandler(405)
    def method_not_allowed_error(error):
        """Handle 405 errors"""
        logger.warning(f"405 error: {request.method} {request.url}")

        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Method not allowed'}), 405

        return render_template('errors/405.html'), 405

    @app_or_blueprint.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"500 error: {request.url} - {str(error)}")

        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500

        return render_template('errors/500.html'), 500

    @app_or_blueprint.errorhandler(Exception)
    def handle_exception(error):
        """Handle all other exceptions"""
        logger.error(f"Unhandled exception: {request.url} - {str(error)}", exc_info=True)

        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'An unexpected error occurred'}), 500

        # For non-API requests, try to render error page, fallback to simple response
        try:
            return render_template('errors/500.html'), 500
        except Exception:
            return "<h1>Internal Server Error</h1><p>An unexpected error occurred.</p>", 500
