"""
RAG (Retrieval-Augmented Generation) management API blueprint
"""

from flask import Blueprint, jsonify, request

from web_app.services.rag_service import rag_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

api_rag = Blueprint('api_rag', __name__, url_prefix='/api/rag')


@api_rag.route('/corpora', methods=['GET'])
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


@api_rag.route('/corpora', methods=['POST'])
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


@api_rag.route('/corpora/<corpus_id>/load-pdf-text', methods=['POST'])
def load_pdf_text(corpus_id):
    """Load PDF text files into corpus"""
    try:
        result = rag_service.load_pdf_text_files(corpus_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading PDF text: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_rag.route('/sessions', methods=['POST'])
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


@api_rag.route('/search', methods=['POST'])
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


@api_rag.route('/query', methods=['POST'])
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


@api_rag.route('/corpora/<corpus_id>/stats')
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
