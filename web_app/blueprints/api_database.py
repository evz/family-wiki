"""
Database management API blueprint
"""

from flask import Blueprint, jsonify

from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

api_database = Blueprint('api_database', __name__, url_prefix='/api/database')


@api_database.route('/stats')
def get_database_stats():
    """Get database statistics"""
    try:
        repository = GenealogyDataRepository()
        stats = repository.get_database_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_database.route('/clear', methods=['POST'])
def clear_database():
    """Clear all extraction data from the database"""
    try:
        from web_app.database import db
        from web_app.database.models import Event, Family, Marriage, Person

        # Delete in order to respect foreign key constraints
        Family.query.delete()
        Marriage.query.delete()
        Event.query.delete()
        Person.query.delete()
        db.session.commit()

        logger.info("Database cleared via API")
        return jsonify({
            'success': True,
            'message': 'Database cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
