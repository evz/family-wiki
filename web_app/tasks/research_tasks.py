"""
Celery tasks for research question generation
"""
import json
from pathlib import Path

from celery import current_task
from celery.exceptions import Retry
from sqlalchemy.exc import SQLAlchemyError

from web_app.repositories.job_file_repository import JobFileRepository
from web_app.research_question_generator import ResearchQuestionGenerator
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


@celery.task(bind=True, autoretry_for=(FileNotFoundError, IOError), retry_kwargs={'max_retries': 3, 'countdown': 60})
def generate_research_questions(self, input_file: str = None, output_file: str = None):
    """
    Generate research questions from extracted genealogy data

    Args:
        input_file: Path to input JSON file (optional, defaults to llm_genealogy_results.json)
        output_file: Path to output file (optional, auto-generated)

    Returns:
        dict: Research question generation results with file path
    """
    try:
        # Update task status
        current_task.update_state(
            state='RUNNING',
            meta={'status': 'initializing', 'progress': 0}
        )

        # Set default input file
        if not input_file:
            input_file = "web_app/pdf_processing/llm_genealogy_results.json"

        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        if not input_path.is_file():
            raise ValueError(f"Input path is not a file: {input_file}")

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

        # Save research questions as downloadable JSON file
        try:
            file_repo = JobFileRepository()

            # Create JSON content for download
            json_content = json.dumps(result, indent=2, ensure_ascii=False).encode('utf-8')

            # Generate filename
            filename = f"research_questions_{current_task.request.id[:8]}.json"

            # Save as downloadable file
            file_repo.save_job_file(
                task_id=current_task.request.id,
                filename=filename,
                file_data=json_content,
                content_type='application/json',
                file_type='output'
            )

            result['download_available'] = True
            logger.info(f"Research questions saved for download: {filename}")

        except SQLAlchemyError as e:
            logger.error(f"Database error saving research questions for download: {e}")
            result['download_available'] = False
        except (OSError, PermissionError) as e:
            logger.error(f"File system error saving research questions for download: {e}")
            result['download_available'] = False
        except Exception as e:
            logger.error(f"Unexpected error saving research questions for download: {e}")
            result['download_available'] = False

        logger.info(f"Research question generation completed successfully: {result}")
        return result

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'File not found: {str(e)}'}
        )
        raise

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'Invalid input: {str(e)}'}
        )
        raise

    except RuntimeError as e:
        logger.error(f"Research question generation failed: {e}", exc_info=True)
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': str(e)}
        )
        raise

    except (OSError, PermissionError) as e:
        logger.error(f"IO error (will retry): {e}")
        current_task.update_state(
            state='RETRY',
            meta={'status': 'retrying', 'error': f'IO error: {str(e)}'}
        )
        raise Retry(f"IO error: {e}") from e

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'Missing dependency: {str(e)}'}
        )
        raise
