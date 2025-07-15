"""
RAG (Retrieval-Augmented Generation) blueprint for querying source documents
"""

from flask import Blueprint, render_template

from web_app.database.models import QuerySession
from web_app.services.rag_service import rag_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

rag = Blueprint('rag', __name__, url_prefix='/rag')


@rag.route('/')
def index():
    """RAG query interface"""
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
