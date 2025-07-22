"""
Celery tasks for OCR processing
"""
from pathlib import Path

from celery import current_task
from celery.exceptions import Retry

from web_app.pdf_processing.ocr_processor import PDFOCRProcessor
from web_app.repositories.job_file_repository import JobFileRepository
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.celery_app import celery_app


logger = get_project_logger(__name__)


class OCRTaskManager:
    """Manages OCR processing workflow with proper error handling"""

    def __init__(self, task_id: str, pdf_folder_path: str = None):
        self.task_id = task_id
        self.pdf_folder_path = pdf_folder_path or "web_app/pdf_processing/pdfs"
        self.pdf_folder = Path(self.pdf_folder_path)
        self.processor = None
        self.pdf_files = []
        self.temp_files = []
        self.file_repo = JobFileRepository()

    def _validate_paths(self):
        """Validate input and output paths"""
        if not self.pdf_folder.exists():
            raise FileNotFoundError(f"PDF folder not found: {self.pdf_folder}")

        if not self.pdf_folder.is_dir():
            raise NotADirectoryError(f"PDF path is not a directory: {self.pdf_folder}")

        # Create output folder if it doesn't exist
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create output folder {self.output_folder}: {e}") from e

    def _get_pdf_files(self):
        """Get list of PDF files to process (from uploads or folder)"""
        try:
            # First check if there are uploaded files for this task
            self.temp_files = self.file_repo.create_temp_files_from_uploads(self.task_id, 'input')

            if self.temp_files:
                # Use uploaded files
                self.pdf_files = [Path(f) for f in self.temp_files]
                logger.info(f"Found {len(self.pdf_files)} uploaded PDF files to process")
                return True

            # Fall back to folder-based processing
            self.pdf_files = list(self.pdf_folder.glob("*.pdf"))
            if not self.pdf_files:
                logger.warning(f"No PDF files found in {self.pdf_folder}")
                return False

            logger.info(f"Found {len(self.pdf_files)} PDF files to process from folder")
            return True

        except PermissionError as e:
            raise PermissionError(f"Cannot access PDF folder {self.pdf_folder}: {e}") from e

    def _process_single_pdf(self, pdf_file: Path, output_file: Path) -> bool:
        """Process a single PDF file"""
        try:
            return self.processor.process_single_pdf(pdf_file, output_file)
        except FileNotFoundError:
            logger.error(f"PDF file disappeared during processing: {pdf_file}")
            return False
        except PermissionError as e:
            logger.error(f"Permission denied processing {pdf_file}: {e}")
            return False
        except ValueError as e:
            logger.error(f"Invalid PDF file {pdf_file}: {e}")
            return False
        except RuntimeError as e:
            logger.error(f"OCR processing failed for {pdf_file}: {e}")
            return False

    def _create_consolidated_text_file(self, processed_files):
        """Create consolidated text file from processed files and save to database"""
        try:
            consolidated_content = []

            # Sort processed files by filename for proper ordering
            sorted_files = sorted(processed_files, key=lambda x: x['output_file'])

            for file_info in sorted_files:
                output_file = Path(file_info['output_file'])
                if output_file.exists():
                    try:
                        with open(output_file, encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                consolidated_content.append(f"=== {output_file.name} ===\n\n")
                                consolidated_content.append(content)
                                consolidated_content.append("\n\n")
                    except UnicodeDecodeError as e:
                        logger.warning(f"Encoding error reading {output_file}: {e}")
                    except OSError as e:
                        logger.warning(f"IO error reading {output_file}: {e}")

            # Save consolidated content to database
            consolidated_text = "".join(consolidated_content)
            file_id = self.file_repo.save_result_file(
                filename="consolidated_text.txt",
                content=consolidated_text,
                content_type="text/plain",
                task_id=self.task_id,
                job_type="ocr"
            )

            if file_id:
                logger.info(f"Saved consolidated text file to database for task {self.task_id}")
                return file_id
            else:
                logger.error("Failed to save consolidated text file to database")
                return None

        except Exception as e:
            logger.error(f"Error creating consolidated text file: {e}")
            raise

    def run_ocr_processing(self):
        """Run the complete OCR processing workflow"""
        # Initialize
        current_task.update_state(
            state='RUNNING',
            meta={'status': 'initializing', 'progress': 0}
        )

        self._validate_paths()

        if not self._get_pdf_files():
            return {
                'success': True,
                'message': 'No PDF files found to process',
                'files_processed': 0,
                'output_folder': str(self.output_folder)
            }

        current_task.update_state(
            state='RUNNING',
            meta={
                'status': 'processing',
                'progress': 5,
                'total_files': len(self.pdf_files),
                'current_file': 0
            }
        )

        # Create OCR processor
        self.processor = PDFOCRProcessor()

        # Process each PDF
        processed_files = []
        failed_files = []

        for i, pdf_file in enumerate(self.pdf_files):
            current_file = i + 1
            progress = int((i / len(self.pdf_files)) * 85) + 5  # 5-90% for processing

            logger.info(f"Processing PDF {current_file}/{len(self.pdf_files)}: {pdf_file.name}")

            current_task.update_state(
                state='RUNNING',
                meta={
                    'status': 'processing',
                    'progress': progress,
                    'total_files': len(self.pdf_files),
                    'current_file': current_file,
                    'current_filename': pdf_file.name
                }
            )

            output_file = self.output_folder / f"{pdf_file.stem}.txt"
            success = self._process_single_pdf(pdf_file, output_file)

            if success:
                processed_files.append({
                    'input_file': str(pdf_file),
                    'output_file': str(output_file),
                    'size': output_file.stat().st_size if output_file.exists() else 0
                })
            else:
                failed_files.append(str(pdf_file))

        # Create consolidated text file
        current_task.update_state(
            state='RUNNING',
            meta={
                'status': 'consolidating',
                'progress': 95,
                'total_files': len(self.pdf_files),
                'current_file': len(self.pdf_files)
            }
        )

        consolidated_file_id = self._create_consolidated_text_file(processed_files)

        # Clean up temporary files
        if self.temp_files:
            self.file_repo.cleanup_temp_files(self.temp_files)

        # Return results
        return {
            'success': True,
            'files_processed': len(processed_files),
            'files_failed': len(failed_files),
            'total_files': len(self.pdf_files),
            'consolidated_file_id': consolidated_file_id,
            'processed_files': processed_files,
            'failed_files': failed_files
        }


@celery_app.task(bind=True, autoretry_for=(ConnectionError, IOError), retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_pdfs_ocr(self, pdf_folder_path: str = None):
    """
    Process PDFs using OCR and extract text

    Args:
        pdf_folder_path: Path to folder containing PDFs (optional, defaults to web_app/pdf_processing/pdfs)

    Returns:
        dict: OCR results with file paths and statistics
    """
    task_manager = OCRTaskManager(self.request.id, pdf_folder_path)

    try:
        result = task_manager.run_ocr_processing()
        logger.info(f"OCR processing completed successfully: {result}")
        return result

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'File not found: {str(e)}'}
        )
        raise

    except NotADirectoryError as e:
        logger.error(f"Directory error: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'Directory error: {str(e)}'}
        )
        raise

    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'Permission denied: {str(e)}'}
        )
        raise

    except ConnectionError as e:
        logger.error(f"Connection error (will retry): {e}")
        current_task.update_state(
            state='RETRY',
            meta={'status': 'retrying', 'error': f'Connection error: {str(e)}'}
        )
        raise Retry(f"Connection error: {e}") from e

    except OSError as e:
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

    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'Runtime error: {str(e)}'}
        )
        raise
