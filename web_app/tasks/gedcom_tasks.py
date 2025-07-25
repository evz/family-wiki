"""
Celery tasks for GEDCOM generation
"""
from pathlib import Path

from celery import current_task
from celery.exceptions import Retry
from sqlalchemy.exc import SQLAlchemyError

from web_app.repositories.job_file_repository import JobFileRepository
from web_app.services.gedcom_service import gedcom_service
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


@celery.task(bind=True, autoretry_for=(FileNotFoundError, IOError), retry_kwargs={'max_retries': 3, 'countdown': 60})
def generate_gedcom_file(self, input_file: str = None, output_file: str = None):
    """
    Generate GEDCOM file from extracted genealogy data

    Args:
        input_file: Path to input JSON file (optional, defaults to llm_genealogy_results.json)
        output_file: Path to output GEDCOM file (optional, auto-generated)

    Returns:
        dict: GEDCOM generation results with file path
    """
    try:
        # Update task status
        current_task.update_state(
            state='RUNNING',
            meta={'status': 'initializing', 'progress': 0}
        )

        # Validate input file
        if input_file:
            input_path = Path(input_file)
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")
            if not input_path.is_file():
                raise ValueError(f"Input path is not a file: {input_file}")

        current_task.update_state(
            state='RUNNING',
            meta={'status': 'generating', 'progress': 10}
        )

        # Generate GEDCOM using the service
        result = gedcom_service.generate_gedcom(
            input_file=input_file,
            output_file=output_file
        )

        current_task.update_state(
            state='RUNNING',
            meta={'status': 'finalizing', 'progress': 90}
        )

        if result['success']:
            # Save the GEDCOM file to the job repository for download
            try:
                file_repo = JobFileRepository()
                output_file_path = result['output_file']

                # Read the generated GEDCOM file
                with open(output_file_path, 'rb') as f:
                    gedcom_content = f.read()

                # Save as downloadable file
                file_repo.save_job_file(
                    task_id=current_task.request.id,
                    filename=Path(output_file_path).name,
                    file_data=gedcom_content,
                    content_type='application/x-gedcom',
                    file_type='output'
                )

                result['download_available'] = True
                logger.info(f"GEDCOM file saved for download: {output_file_path}")

            except SQLAlchemyError as e:
                logger.error(f"Database error saving GEDCOM file for download: {e}")
                result['download_available'] = False
            except (OSError, PermissionError) as e:
                logger.error(f"File system error saving GEDCOM file for download: {e}")
                result['download_available'] = False
            except Exception as e:
                logger.error(f"Unexpected error saving GEDCOM file for download: {e}")
                result['download_available'] = False

            logger.info(f"GEDCOM generation completed successfully: {result}")
            return result
        else:
            raise RuntimeError(f"GEDCOM generation failed: {result.get('error', 'Unknown error')}")

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
        logger.error(f"GEDCOM generation failed: {e}")
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
