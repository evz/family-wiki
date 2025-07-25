"""
RAG (Retrieval-Augmented Generation) blueprint for querying source documents
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from web_app.database.models import QuerySession
from web_app.services.exceptions import (
    ConnectionError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    TimeoutError,
    ValidationError,
)
from web_app.services.rag_service import RAGService
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

rag = Blueprint('rag', __name__, url_prefix='/rag')




@rag.route('/')
def index():
    """RAG query interface"""
    rag_service = RAGService()
    corpora = rag_service.get_all_corpora()
    active_corpus = rag_service.get_active_corpus()

    corpus_stats = {}
    if active_corpus:
        corpus_stats = rag_service.get_corpus_stats(str(active_corpus.id))

    return render_template('rag/index.html',
                         corpora=corpora,
                         active_corpus=active_corpus,
                         corpus_stats=corpus_stats)


@rag.route('/corpora')
def corpora_list():
    """List all text corpora"""
    rag_service = RAGService()
    corpora = rag_service.get_all_corpora()
    return render_template('rag/corpora.html', corpora=corpora)


@rag.route('/sessions')
def sessions_list():
    """List all query sessions"""
    sessions = QuerySession.query.order_by(QuerySession.created_at.desc()).all()
    return render_template('rag/sessions.html', sessions=sessions)


@rag.route('/sessions/<session_id>')
def session_detail(session_id):
    """Show query session with all queries"""
    session = QuerySession.query.get_or_404(session_id)
    return render_template('rag/session_detail.html', session=session)


@rag.route('/submit-query', methods=['POST'])
def submit_query():
    """Submit a new RAG query"""
    try:
        question = request.form.get('question', '').strip()
        session_name = request.form.get('session_name', '').strip()

        if not question:
            flash('Question is required', 'error')
            return redirect(url_for('rag.index'))

        rag_service = RAGService()
        active_corpus = rag_service.get_active_corpus()

        if not active_corpus:
            flash('No active corpus available for queries', 'error')
            return redirect(url_for('rag.index'))

        # Create or get query session
        session = _get_or_create_session(rag_service, active_corpus.id, session_name)

        # Generate RAG response
        query_result = rag_service.generate_rag_response(question, str(session.id))

        flash(f'Query submitted successfully! Generated response with {len(query_result.retrieved_sources)} sources.', 'success')
        return redirect(url_for('rag.session_detail', session_id=session.id))

    except ValidationError as e:
        flash(f'Invalid input: {str(e)}', 'error')
    except NotFoundError as e:
        flash(f'Resource not found: {str(e)}', 'error')
    except ConnectionError:
        flash('Unable to connect to language model service. Please try again later.', 'error')
    except TimeoutError:
        flash('Request timed out. Please try again with a shorter question.', 'error')
    except ExternalServiceError:
        flash('Language model service is currently unavailable. Please try again later.', 'error')
    except DatabaseError:
        flash('Database error occurred. Please try again.', 'error')

    return redirect(url_for('rag.index'))




def _get_or_create_session(rag_service, corpus_id, session_name=None):
    """Helper function to get or create query session"""
    if session_name:
        existing_session = QuerySession.query.filter_by(session_name=session_name).first()
        if existing_session:
            return existing_session

    return rag_service.create_query_session(str(corpus_id), session_name)
