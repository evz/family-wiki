"""
API blueprint for web interface endpoints
"""

from flask import Blueprint, jsonify, request

from web_app.services.benchmark_service import benchmark_service
from web_app.services.extraction_service import extraction_service
from web_app.services.gedcom_service import gedcom_service
from web_app.services.ocr_service import ocr_service
from web_app.services.prompt_service import prompt_service
from web_app.services.rag_service import rag_service
from web_app.services.research_service import research_service
from web_app.services.system_service import system_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/status')
def status():
    """API endpoint to check system status"""
    system_status = system_service.check_system_status()
    return jsonify(system_status)


@api.route('/status/refresh')
def refresh_status():
    """API endpoint to refresh system status (for testing)"""
    system_status = system_service.check_system_status()
    return jsonify(system_status)


@api.route('/run/<tool>')
def run_tool(tool):
    """API endpoint to run tools using shared services"""
    valid_tools = ['ocr', 'benchmark', 'extract', 'gedcom', 'research']

    if tool not in valid_tools:
        return jsonify({'error': f'Invalid tool: {tool}'}), 400

    try:
        # Route to appropriate service
        if tool == 'ocr':
            result = ocr_service.process_pdfs()
        elif tool == 'benchmark':
            result = benchmark_service.run_benchmark()
        elif tool == 'extract':
            # For extraction, redirect to the extraction blueprint
            task_id = extraction_service.start_extraction()
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Extraction started',
                'redirect': f'/api/extraction/status/{task_id}'
            })
        elif tool == 'gedcom':
            result = gedcom_service.generate_gedcom()
        elif tool == 'research':
            result = research_service.generate_questions()

        # Convert service result to web API format
        if result['success']:
            return jsonify({
                'success': True,
                'stdout': result.get('message', ''),
                'stderr': '',
                'return_code': 0,
                'results': result.get('results', {})
            })
        else:
            return jsonify({
                'success': False,
                'stdout': '',
                'stderr': result.get('error', 'Unknown error'),
                'return_code': 1
            })

    except Exception as e:
        logger.error(f"Error running tool {tool}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stderr': str(e),
            'return_code': 1
        }), 500


# Prompt Management Routes

@api.route('/prompts', methods=['GET'])
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


@api.route('/prompts/<prompt_id>', methods=['GET'])
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


@api.route('/prompts', methods=['POST'])
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


@api.route('/prompts/<prompt_id>', methods=['PUT'])
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


@api.route('/prompts/<prompt_id>/activate', methods=['POST'])
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


@api.route('/prompts/<prompt_id>', methods=['DELETE'])
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


@api.route('/prompts/<prompt_id>/reset', methods=['POST'])
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


# Database Management Routes

@api.route('/database/stats')
def get_database_stats():
    """Get database statistics"""
    try:
        stats = extraction_service.get_database_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/database/clear', methods=['POST'])
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


# RAG Management Routes

@api.route('/rag/corpora', methods=['GET'])
def get_corpora():
    """Get all text corpora"""
    try:
        corpora = rag_service.get_all_corpora()
        return jsonify({
            'success': True,
            'corpora': [
                {
                    'id': str(corpus.id),
                    'name': corpus.name,
                    'description': corpus.description,
                    'is_active': corpus.is_active,
                    'chunk_count': corpus.chunk_count,
                    'created_at': corpus.created_at.isoformat()
                }
                for corpus in corpora
            ]
        })
    except Exception as e:
        logger.error(f"Error getting corpora: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/rag/corpora', methods=['POST'])
def create_corpus():
    """Create a new text corpus"""
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        corpus = rag_service.create_corpus(
            name=data['name'],
            description=data.get('description', '')
        )

        return jsonify({
            'success': True,
            'corpus': {
                'id': str(corpus.id),
                'name': corpus.name,
                'description': corpus.description
            }
        })
    except Exception as e:
        logger.error(f"Error creating corpus: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/rag/corpora/<corpus_id>/load-pdf-text', methods=['POST'])
def load_pdf_text(corpus_id):
    """Load PDF text files into corpus"""
    try:
        result = rag_service.load_pdf_text_files(corpus_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading PDF text: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/rag/sessions', methods=['POST'])
def create_rag_session():
    """Create a new query session"""
    try:
        data = request.get_json()
        corpus_id = data.get('corpus_id')
        session_name = data.get('session_name')

        if not corpus_id:
            # Use active corpus
            active_corpus = rag_service.get_active_corpus()
            if not active_corpus:
                return jsonify({'success': False, 'error': 'No active corpus found'}), 400
            corpus_id = str(active_corpus.id)

        session = rag_service.create_query_session(corpus_id, session_name)

        return jsonify({
            'success': True,
            'session': {
                'id': str(session.id),
                'name': session.session_name,
                'corpus_id': str(session.corpus_id)
            }
        })
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/rag/search', methods=['POST'])
def semantic_search():
    """Perform semantic search"""
    try:
        data = request.get_json()
        query_text = data.get('query')
        corpus_id = data.get('corpus_id')
        limit = data.get('limit', 5)

        if not query_text:
            return jsonify({'success': False, 'error': 'Query text is required'}), 400

        results = rag_service.semantic_search(query_text, corpus_id, limit)

        return jsonify({
            'success': True,
            'results': [
                {
                    'id': str(chunk.id),
                    'filename': chunk.filename,
                    'page_number': chunk.page_number,
                    'chunk_number': chunk.chunk_number,
                    'content': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content,
                    'similarity': similarity
                }
                for chunk, similarity in results
            ]
        })
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/rag/query', methods=['POST'])
def rag_query():
    """Submit a RAG query"""
    try:
        data = request.get_json()
        question = data.get('question')
        session_id = data.get('session_id')

        if not question:
            return jsonify({'success': False, 'error': 'Question is required'}), 400

        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID is required'}), 400

        query = rag_service.generate_rag_response(question, session_id)

        return jsonify({
            'success': True,
            'query': {
                'id': str(query.id),
                'question': query.question,
                'answer': query.answer,
                'status': query.status,
                'error_message': query.error_message,
                'retrieved_chunks': query.retrieved_chunks,
                'similarity_scores': query.similarity_scores
            }
        })
    except Exception as e:
        logger.error(f"Error processing RAG query: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/rag/corpora/<corpus_id>/stats')
def get_corpus_stats(corpus_id):
    """Get corpus statistics"""
    try:
        stats = rag_service.get_corpus_stats(corpus_id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting corpus stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
