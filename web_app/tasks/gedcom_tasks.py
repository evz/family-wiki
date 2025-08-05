"""
Celery tasks for GEDCOM generation
"""
from pathlib import Path

from celery import current_task
from sqlalchemy.exc import SQLAlchemyError

from web_app.services.gedcom_service import GedcomService
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.base_task import BaseFileProcessingTask, FileResultMixin
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


def _generate_gedcom_with_progress(input_file: str = None, output_file: str = None):
    """Internal method to generate GEDCOM with progress tracking"""
    task_handler = BaseFileProcessingTask()
    file_handler = FileResultMixin()
    
    # Update task status
    current_task.update_state(
        state='RUNNING',
        meta={'status': 'initializing', 'progress': 0}
    )

    # Validate input file
    if input_file:
        task_handler.validate_file_path(input_file, must_exist=True, must_be_file=True)

    current_task.update_state(
        state='RUNNING',
        meta={'status': 'generating', 'progress': 10}
    )

    # Generate GEDCOM using the service
    gedcom_service = GedcomService()
    result = gedcom_service.generate_gedcom(
        input_file=input_file,
        output_file=output_file
    )

    current_task.update_state(
        state='RUNNING',
        meta={'status': 'finalizing', 'progress': 90}
    )

    if result['success']:
        # Save the GEDCOM file for download
        try:
            output_file_path = result['output_file']

            # Read the generated GEDCOM file
            with open(output_file_path, 'rb') as f:
                gedcom_content = f.read()

            # Save as downloadable file using mixin
            file_saved = file_handler.save_result_file(
                filename=Path(output_file_path).name,
                content=gedcom_content,
                content_type='application/x-gedcom',
                task_id=current_task.request.id
            )

            result['download_available'] = bool(file_saved)
            if file_saved:
                logger.info(f"GEDCOM file saved for download: {output_file_path}")

        except Exception as e:
            logger.error(f"Error saving GEDCOM file for download: {e}")
            result['download_available'] = False

        logger.info(f"GEDCOM generation completed successfully: {result}")
        return result
    else:
        raise RuntimeError(f"GEDCOM generation failed: {result.get('error', 'Unknown error')}")


@celery.task(bind=True, autoretry_for=BaseFileProcessingTask.autoretry_for, 
             retry_kwargs=BaseFileProcessingTask.retry_kwargs)
def generate_gedcom_file(self, input_file: str = None, output_file: str = None):
    """
    Generate GEDCOM file from extracted genealogy data

    Args:
        input_file: Path to input JSON file (optional, defaults to llm_genealogy_results.json)
        output_file: Path to output GEDCOM file (optional, auto-generated)

    Returns:
        dict: GEDCOM generation results with file path
    """
    task_handler = BaseFileProcessingTask()
    return task_handler.execute_with_error_handling(
        _generate_gedcom_with_progress, input_file, output_file
    )
