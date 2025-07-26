"""
RAG (Retrieval-Augmented Generation) blueprint for querying source documents
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from web_app.blueprints.error_handling import handle_blueprint_errors, safe_task_submit
from web_app.database import db
from web_app.database.models import TextCorpus
from web_app.services.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    get_available_embedding_models,
    validate_embedding_model,
)
from web_app.services.exceptions import (
    ConnectionError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    TimeoutError,
    ValidationError,
)
from web_app.services.prompt_service import PromptService
from web_app.services.rag_service import RAGService
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.rag_tasks import process_corpus


logger = get_project_logger(__name__)

rag = Blueprint('rag', __name__, url_prefix='/rag')




@rag.route('/')
def index():
    """RAG query interface"""
    rag_service = RAGService()

    corpora = rag_service.get_all_corpora()

    # Get RAG prompts for the user to choose from
    prompt_service = PromptService()
    rag_prompts = prompt_service.get_all_prompts(prompt_type='rag')

    return render_template('rag/index.html',
                         corpora=corpora,
                         rag_prompts=rag_prompts)


@rag.route('/corpora')
def corpora_list():
    """List all text corpora"""
    rag_service = RAGService()
    corpora = rag_service.get_all_corpora()
    return render_template('rag/corpora.html', corpora=corpora)


@rag.route('/corpora/create', methods=['GET', 'POST'])
@handle_blueprint_errors()
def create_corpus():
    """Create a new text corpus with uploaded content"""
    # Get available embedding models for the form
    available_models = get_available_embedding_models()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        embedding_model = request.form.get('embedding_model', DEFAULT_EMBEDDING_MODEL).strip()
        text_file = request.files.get('text_file')

        # Validate required fields
        if not name:
            flash('Corpus name is required', 'error')
            return render_template('rag/create_corpus.html', available_models=available_models)

        if not text_file or text_file.filename == '':
            flash('Text file is required', 'error')
            return render_template('rag/create_corpus.html', available_models=available_models)

        # Validate embedding model
        if not validate_embedding_model(embedding_model):
            flash('Invalid embedding model selected', 'error')
            return render_template('rag/create_corpus.html', available_models=available_models)

        # Validate file type
        if not text_file.filename.lower().endswith('.txt'):
            flash('Only .txt files are supported', 'error')
            return render_template('rag/create_corpus.html', available_models=available_models)

        # Read file content
        try:
            content = text_file.read().decode('utf-8')
            if not content.strip():
                flash('File is empty or contains no readable text', 'error')
                return render_template('rag/create_corpus.html', available_models=available_models)
        except UnicodeDecodeError:
            flash('File must be valid UTF-8 encoded text', 'error')
            return render_template('rag/create_corpus.html', available_models=available_models)

        # Create corpus with raw content and selected embedding model
        rag_service = RAGService()
        corpus = rag_service.create_corpus(name, description)

        # Store the raw content and embedding model in the corpus
        corpus.raw_content = content
        corpus.embedding_model = embedding_model
        corpus.processing_status = 'pending'
        db.session.commit()

        # Start background processing task
        task = safe_task_submit(
            process_corpus.delay,
            "corpus processing",
            str(corpus.id)
        )

        if task:
            flash(f'Corpus "{corpus.name}" created and processing started! Task ID: {task.id}', 'success')
            logger.info(f"Started corpus processing task: {task.id} for corpus: {corpus.id}")
        else:
            flash(f'Corpus "{corpus.name}" created but processing could not be started', 'warning')

        return redirect(url_for('rag.corpora_list'))

    return render_template('rag/create_corpus.html', available_models=available_models)






@rag.route('/ask-question', methods=['POST'])
@handle_blueprint_errors()
def ask_question():
    """Submit a simplified RAG query without QuerySession complexity"""
    try:
        question = request.form.get('question', '').strip()
        corpus_id = request.form.get('corpus_id', '').strip()
        prompt_id = request.form.get('prompt_id', '').strip()

        if not question:
            flash('Question is required', 'error')
            return redirect(url_for('rag.index'))

        if not corpus_id:
            flash('Please select a corpus to query', 'error')
            return redirect(url_for('rag.index'))

        if not prompt_id:
            flash('Please select a RAG prompt to use', 'error')
            return redirect(url_for('rag.index'))

        rag_service = RAGService()

        # Validate that the selected corpus exists and is ready
        selected_corpus = db.session.get(TextCorpus, corpus_id)
        if not selected_corpus:
            flash('Selected corpus not found', 'error')
            return redirect(url_for('rag.index'))

        if selected_corpus.processing_status != 'completed':
            flash(f'Corpus "{selected_corpus.name}" is not ready for queries (status: {selected_corpus.processing_status})', 'error')
            return redirect(url_for('rag.index'))

        # Ask the question using simplified method
        result = rag_service.ask_question(
            question=question,
            prompt_id=prompt_id,
            corpus_id=corpus_id
        )

        # Store result in session or flash for display
        # For now, we'll use flash to show the answer
        flash(f'Answer: {result["answer"]}', 'success')
        return redirect(url_for('rag.index'))

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


