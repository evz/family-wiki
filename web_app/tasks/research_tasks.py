"""
Celery tasks for research question generation
"""
import json
from pathlib import Path

from celery import current_task
from sqlalchemy.exc import SQLAlchemyError

from web_app.research_question_generator import ResearchQuestionGenerator
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.base_task import BaseFileProcessingTask, FileResultMixin
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


def _generate_research_questions_with_progress(input_file: str = None, output_file: str = None):
    """Internal method to generate research questions with progress tracking"""
    task_handler = BaseFileProcessingTask()
    file_handler = FileResultMixin()
    
    # Update task status
    current_task.update_state(
        state='RUNNING',
        meta={'status': 'initializing', 'progress': 0}
    )

    # Set default input file
    if not input_file:
        input_file = "web_app/pdf_processing/llm_genealogy_results.json"

    # Validate input file
    task_handler.validate_file_path(input_file, must_exist=True, must_be_file=True)

    current_task.update_state(
        state='RUNNING',
        meta={'status': 'generating', 'progress': 10}
    )

    # Create research question generator
    generator = ResearchQuestionGenerator(input_file)

    current_task.update_state(
        state='RUNNING',
        meta={'status': 'processing', 'progress': 50}
    )

    # Generate questions
    questions = generator.generate_all_questions()

    current_task.update_state(
        state='RUNNING',
        meta={'status': 'saving', 'progress': 90}
    )

    # Save results to file if output_file specified
    if output_file:
        output_path = Path(output_file)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if isinstance(questions, dict):
                    json.dump(questions, f, indent=2, ensure_ascii=False)
                else:
                    f.write(str(questions))

            result = {
                'success': True,
                'questions': questions,
                'output_file': str(output_path),
                'input_file': input_file,
                'total_questions': len(questions) if isinstance(questions, list) else 0
            }
        except (OSError, PermissionError) as e:
            raise OSError(f"Failed to save output file: {e}") from e
    else:
        # Return questions without saving
        result = {
            'success': True,
            'questions': questions,
            'input_file': input_file,
            'total_questions': len(questions) if isinstance(questions, list) else 0
        }

    # Save research questions as downloadable JSON file using mixin
    try:
        # Create JSON content for download
        json_content = json.dumps(result, indent=2, ensure_ascii=False).encode('utf-8')

        # Generate filename
        filename = f"research_questions_{current_task.request.id[:8]}.json"

        # Save as downloadable file using mixin
        file_saved = file_handler.save_result_file(
            filename=filename,
            content=json_content,
            content_type='application/json',
            task_id=current_task.request.id
        )

        result['download_available'] = bool(file_saved)
        if file_saved:
            logger.info(f"Research questions saved for download: {filename}")

    except Exception as e:
        logger.error(f"Error saving research questions for download: {e}")
        result['download_available'] = False

    logger.info(f"Research question generation completed successfully: {result}")
    return result


@celery.task(bind=True, autoretry_for=BaseFileProcessingTask.autoretry_for, 
             retry_kwargs=BaseFileProcessingTask.retry_kwargs)
def generate_research_questions(self, input_file: str = None, output_file: str = None):
    """
    Generate research questions from extracted genealogy data

    Args:
        input_file: Path to input JSON file (optional, defaults to llm_genealogy_results.json)
        output_file: Path to output file (optional, auto-generated)

    Returns:
        dict: Research question generation results with file path
    """
    task_handler = BaseFileProcessingTask()
    return task_handler.execute_with_error_handling(
        _generate_research_questions_with_progress, input_file, output_file
    )
