"""
Celery tasks for OCR processing
"""
from pathlib import Path

from celery import current_task

from web_app.pdf_processing.ocr_processor import PDFOCRProcessor
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.base_task import BaseTaskManager, FileResultMixin, BaseFileProcessingTask
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


class OCRTaskManager(BaseTaskManager, FileResultMixin):
    """Manages OCR processing workflow with proper error handling"""

    def __init__(self, task_id: str, pdf_folder_path: str = None):
        super().__init__(task_id)
        self.pdf_folder_path = pdf_folder_path or "web_app/pdf_processing/pdfs"
        self.pdf_folder = Path(self.pdf_folder_path)
        self.output_folder = self.pdf_folder / "extracted_text"  # Add missing output_folder attribute
        self.processor = None
        self.pdf_files = []

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
            # Extract text from PDF
            extracted_text = self.processor.process_pdf(pdf_file)
            
            # Write text to output file
            output_file.write_text(extracted_text, encoding='utf-8')
            
            return bool(extracted_text.strip())  # Return True if we got text
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
            file_id = self.save_result_file(
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

    def run(self):
        """Run the complete OCR processing workflow"""
        # Initialize
        self.update_progress('initializing', 0)

        self._validate_paths()

        if not self._get_pdf_files():
            return {
                'success': True,
                'message': 'No PDF files found to process',
                'files_processed': 0,
                'output_folder': str(self.output_folder)
            }

        self.update_progress(
            'processing', 5,
            total_files=len(self.pdf_files),
            current_file=0
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

            self.update_progress(
                'processing', progress,
                total_files=len(self.pdf_files),
                current_file=current_file,
                current_filename=pdf_file.name
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
        self.update_progress(
            'consolidating', 95,
            total_files=len(self.pdf_files),
            current_file=len(self.pdf_files)
        )

        consolidated_file_id = self._create_consolidated_text_file(processed_files)

        # Clean up temporary files
        self.cleanup_temp_files()

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


@celery.task(bind=True, autoretry_for=BaseFileProcessingTask.autoretry_for, 
             retry_kwargs=BaseFileProcessingTask.retry_kwargs)
def process_pdfs_ocr(self, pdf_folder_path: str = None):
    """
    Process PDFs using OCR and extract text

    Args:
        pdf_folder_path: Path to folder containing PDFs (optional, defaults to web_app/pdf_processing/pdfs)

    Returns:
        dict: OCR results with file paths and statistics
    """
    task_handler = BaseFileProcessingTask()
    task_manager = OCRTaskManager(self.request.id, pdf_folder_path)
    
    return task_handler.execute_with_error_handling(task_manager.run)
