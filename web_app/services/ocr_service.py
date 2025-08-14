"""
OCR service for handling PDF file uploads and OCR task coordination
"""
from typing import List, Callable

from web_app.services.exceptions import ValidationError
from web_app.services.file_job_service import FileJobService, JobResult
from web_app.tasks.ocr_tasks import process_pdfs_ocr


class OCRService(FileJobService):
    """Service for managing OCR operations and file uploads"""
    
    def get_job_type(self) -> str:
        """Return the job type name for OCR operations"""
        return 'ocr'
    
    def get_task_function(self) -> Callable:
        """Return the OCR task function"""
        return process_pdfs_ocr
    
    def get_default_job_message(self, task_id: str) -> str:
        """Return success message for default OCR job"""
        return f'OCR job started using default folder. Task ID: {task_id}'
    
    def get_uploaded_files_message(self, files_count: int, task_id: str) -> str:
        """Return success message for uploaded files OCR job"""
        return f'OCR job started with {files_count} uploaded files. Task ID: {task_id}'
    
    def validate_uploaded_files(self, pdf_files: List) -> bool:
        """Validate uploaded PDF files"""
        if not pdf_files:
            return True  # No files is valid (use default folder)
        
        for pdf_file in pdf_files:
            if pdf_file.filename == '':
                continue
                
            # Check file extension
            if not pdf_file.filename.lower().endswith('.pdf'):
                raise ValidationError(f"File {pdf_file.filename} is not a PDF file")
        
        return True
    
    def start_ocr_job(self, pdf_files: List) -> JobResult:
        """
        Start OCR job with uploaded files or default folder
        
        Args:
            pdf_files: List of uploaded PDF files from Flask request
            
        Returns:
            JobResult: Result of the operation with task details
        """
        return self.start_job(pdf_files)