"""
Prompt management API blueprint
"""

from flask import Blueprint, jsonify, request

from web_app.services.prompt_service import prompt_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

api_prompts = Blueprint('api_prompts', __name__, url_prefix='/api/prompts')


@api_prompts.route('', methods=['GET'])
def get_prompts():
    """Get all prompts"""
    try:
        prompts = prompt_service.get_all_prompts()
        active_prompt = prompt_service.get_active_prompt()

        return jsonify({
            'success': True,
            'prompts': [
                {
                    'id': str(prompt.id),
                    'name': prompt.name,
                    'description': prompt.description,
                    'is_active': prompt.is_active,
                    'created_at': prompt.created_at.isoformat(),
                    'updated_at': prompt.updated_at.isoformat()
                }
                for prompt in prompts
            ],
            'active_prompt_id': str(active_prompt.id) if active_prompt else None
        })
    except Exception as e:
        logger.error(f"Error getting prompts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_prompts.route('/<prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    """Get a specific prompt"""
    try:
        prompts = prompt_service.get_all_prompts()
        prompt = next((p for p in prompts if str(p.id) == prompt_id), None)

        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404

        return jsonify({
            'success': True,
            'prompt': {
                'id': str(prompt.id),
                'name': prompt.name,
                'description': prompt.description,
                'prompt_text': prompt.prompt_text,
                'is_active': prompt.is_active,
                'created_at': prompt.created_at.isoformat(),
                'updated_at': prompt.updated_at.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_prompts.route('', methods=['POST'])
def create_prompt():
    """Create a new prompt"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        name = data.get('name', '').strip()
        prompt_text = data.get('prompt_text', '').strip()
        description = data.get('description', '').strip()

        if not name or not prompt_text:
            return jsonify({'success': False, 'error': 'Name and prompt text are required'}), 400

        prompt = prompt_service.create_prompt(name, prompt_text, description)

        return jsonify({
            'success': True,
            'prompt': {
                'id': str(prompt.id),
                'name': prompt.name,
                'description': prompt.description,
                'is_active': prompt.is_active
            }
        })
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_prompts.route('/<prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update an existing prompt"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        prompt = prompt_service.update_prompt(
            prompt_id,
            name=data.get('name'),
            prompt_text=data.get('prompt_text'),
            description=data.get('description')
        )

        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404

        return jsonify({
            'success': True,
            'prompt': {
                'id': str(prompt.id),
                'name': prompt.name,
                'description': prompt.description,
                'is_active': prompt.is_active
            }
        })
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_prompts.route('/<prompt_id>/activate', methods=['POST'])
def activate_prompt(prompt_id):
    """Set a prompt as active"""
    try:
        success = prompt_service.set_active_prompt(prompt_id)

        if not success:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404

        return jsonify({'success': True, 'message': 'Prompt activated successfully'})
    except Exception as e:
        logger.error(f"Error activating prompt {prompt_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_prompts.route('/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt"""
    try:
        success = prompt_service.delete_prompt(prompt_id)

        if not success:
            return jsonify({'success': False, 'error': 'Cannot delete prompt (active or only remaining prompt)'}), 400

        return jsonify({'success': True, 'message': 'Prompt deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_prompts.route('/<prompt_id>/reset', methods=['POST'])
def reset_prompt_to_default(prompt_id):
    """Reset a prompt to its default content"""
    try:
        # First get the prompt to check its name
        prompts = prompt_service.get_all_prompts()
        prompt = next((p for p in prompts if str(p.id) == prompt_id), None)

        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404

        updated_prompt = prompt_service.reset_to_default(prompt.name)

        if not updated_prompt:
            return jsonify({'success': False, 'error': 'Cannot reset prompt (no default available)'}), 400

        return jsonify({'success': True, 'message': 'Prompt reset to default successfully'})
    except Exception as e:
        logger.error(f"Error resetting prompt {prompt_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
