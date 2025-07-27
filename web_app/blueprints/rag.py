"""
RAG (Retrieval-Augmented Generation) blueprint for querying source documents
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from web_app.blueprints.error_handling import handle_blueprint_errors, safe_task_submit
from web_app.database import db
from web_app.database.models import Query, TextCorpus
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


@rag.route('/corpora/<corpus_id>/delete', methods=['POST'])
@handle_blueprint_errors()
def delete_corpus(corpus_id):
    """Delete a corpus and all its associated data"""
    try:
        rag_service = RAGService()
        result = rag_service.delete_corpus(corpus_id)

        flash(result['message'], 'success')
        return redirect(url_for('rag.corpora_list'))

    except NotFoundError:
        flash('Corpus not found', 'error')
        return redirect(url_for('rag.corpora_list'))
    except Exception as e:
        logger.error(f"Error deleting corpus {corpus_id}: {str(e)}")
        flash('An error occurred while deleting the corpus', 'error')
        return redirect(url_for('rag.corpora_list'))






@rag.route('/ask-question', methods=['POST'])
@handle_blueprint_errors()
def ask_question():
    """Submit a simplified RAG query without QuerySession complexity"""
    try:
        question = request.form.get('question', '').strip()
        corpus_id = request.form.get('corpus_id', '').strip()
        prompt_id = request.form.get('prompt_id', '').strip()
        similarity_threshold = request.form.get('similarity_threshold', '0.55').strip()

        if not question:
            flash('Question is required', 'error')
            return redirect(url_for('rag.index'))

        if not corpus_id:
            flash('Please select a corpus to query', 'error')
            return redirect(url_for('rag.index'))

        if not prompt_id:
            flash('Please select a RAG prompt to use', 'error')
            return redirect(url_for('rag.index'))

        # Validate and convert similarity threshold
        try:
            threshold_float = float(similarity_threshold)
            if not (0.0 <= threshold_float <= 1.0):
                raise ValueError("Threshold must be between 0.0 and 1.0")
        except ValueError:
            flash('Invalid similarity threshold value', 'error')
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

        # Perform hybrid search combining semantic, trigram, full-text, and phonetic matching
        search_results = rag_service.hybrid_search(
            query_text=question,
            corpus_id=corpus_id,
            limit=5
        )

        if not search_results:
            flash(f'No relevant information found for your question with the current search sensitivity ({threshold_float}). Try lowering the sensitivity for broader results.', 'warning')
            return redirect(url_for('rag.index'))

        # Ask the question using simplified method
        result = rag_service.ask_question(
            question=question,
            prompt_id=prompt_id,
            corpus_id=corpus_id,
            similarity_threshold=threshold_float
        )

        # Store result in session or flash for display
        # For now, we'll use flash to show the answer
        chunk_count = len(result["retrieved_chunks"])
        avg_similarity = sum(result["similarity_scores"]) / len(result["similarity_scores"]) if result["similarity_scores"] else 0

        flash(f'Answer: {result["answer"]}', 'success')
        flash(f'Search info: Found {chunk_count} relevant chunks with average similarity {avg_similarity:.2f} using threshold {threshold_float}', 'info')
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


@rag.route('/chat')
def chat_interface():
    """Chat-style conversational RAG interface"""
    rag_service = RAGService()
    corpora = rag_service.get_all_corpora()

    # Get RAG prompts for the user to choose from
    prompt_service = PromptService()
    rag_prompts = prompt_service.get_all_prompts(prompt_type='rag')

    return render_template('rag/chat.html',
                         corpora=corpora,
                         rag_prompts=rag_prompts)


@rag.route('/chat/ask', methods=['POST'])
@handle_blueprint_errors()
def chat_ask():
    """Handle conversational RAG queries with context"""
    try:
        question = request.form.get('question', '').strip()
        corpus_id = request.form.get('corpus_id', '').strip()
        prompt_id = request.form.get('prompt_id', '').strip()
        similarity_threshold = request.form.get('similarity_threshold', '0.55').strip()
        conversation_id = request.form.get('conversation_id', '').strip() or None
        message_sequence = int(request.form.get('message_sequence', '1'))

        # Validate required fields
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'})

        if not corpus_id:
            return jsonify({'success': False, 'error': 'Please select a corpus to query'})

        if not prompt_id:
            return jsonify({'success': False, 'error': 'Please select a RAG prompt to use'})

        # Validate and convert similarity threshold
        try:
            threshold_float = float(similarity_threshold)
            if not (0.0 <= threshold_float <= 1.0):
                raise ValueError("Threshold must be between 0.0 and 1.0")
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid similarity threshold value'})

        # Validate corpus exists and is ready
        selected_corpus = db.session.get(TextCorpus, corpus_id)
        if not selected_corpus:
            return jsonify({'success': False, 'error': 'Selected corpus not found'})

        if selected_corpus.processing_status != 'completed':
            return jsonify({'success': False, 'error': f'Corpus "{selected_corpus.name}" is not ready for queries'})

        # Create or get conversation ID
        if not conversation_id:
            conversation_id = Query.start_new_conversation(corpus_id)
            message_sequence = 1
        else:
            # Convert string UUID back to UUID object
            import uuid
            conversation_id = uuid.UUID(conversation_id)

        # Perform RAG query with conversation context
        rag_service = RAGService()
        result = rag_service.ask_question(
            question=question,
            prompt_id=prompt_id,
            corpus_id=corpus_id,
            similarity_threshold=threshold_float,
            conversation_id=str(conversation_id) if conversation_id else None
        )

        # Store query in database with conversation context
        query = Query(
            corpus_id=corpus_id,
            conversation_id=conversation_id,
            message_sequence=message_sequence,
            question=question,
            answer=result['answer'],
            retrieved_chunks=result.get('retrieved_chunks', []),
            similarity_scores=result.get('similarity_scores', []),
            prompt_used=result.get('prompt_name', ''),
            status='completed'
        )

        db.session.add(query)
        db.session.commit()

        # Return successful response
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'retrieved_chunks': result.get('retrieved_chunks', []),
            'similarity_scores': result.get('similarity_scores', []),
            'conversation_id': str(conversation_id),
            'message_sequence': message_sequence + 1  # Next sequence number
        })

    except ValidationError as e:
        return jsonify({'success': False, 'error': f'Invalid input: {str(e)}'})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': f'Resource not found: {str(e)}'})
    except ConnectionError:
        return jsonify({'success': False, 'error': 'Unable to connect to language model service'})
    except TimeoutError:
        return jsonify({'success': False, 'error': 'Request timed out'})
    except ExternalServiceError:
        return jsonify({'success': False, 'error': 'Language model service is currently unavailable'})
    except DatabaseError:
        return jsonify({'success': False, 'error': 'Database error occurred'})
    except Exception as e:
        logger.error(f"Unexpected error in chat_ask: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred'})


