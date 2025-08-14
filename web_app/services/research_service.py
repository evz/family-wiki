"""
Service for managing research question generation workflows
"""
from typing import List, Callable

from web_app.services.exceptions import ValidationError
from web_app.services.file_job_service import FileJobService, JobResult
from web_app.tasks.research_tasks import generate_research_questions


class ResearchService(FileJobService):
    """Service for managing research question generation operations"""
    
    def get_job_type(self) -> str:
        """Return the job type name for research operations"""
        return 'research'
    
    def get_task_function(self) -> Callable:
        """Return the research task function"""
        return generate_research_questions
    
    def get_default_job_message(self, task_id: str) -> str:
        """Return success message for default research job"""
        return f'Research questions job started using latest extraction results. Task ID: {task_id}'
    
    def get_uploaded_files_message(self, files_count: int, task_id: str) -> str:
        """Return success message for uploaded files research job"""
        return f'Research questions job started with {files_count} uploaded files. Task ID: {task_id}'
    
    def validate_uploaded_files(self, input_files: List) -> bool:
        """Validate uploaded input files"""
        if not input_files:
            return True  # No files is valid (use latest extraction)
        
        for input_file in input_files:
            if input_file.filename == '':
                continue
                
            # Check file extension - research can accept text/json files
            if not (input_file.filename.lower().endswith('.txt') or 
                    input_file.filename.lower().endswith('.json')):
                raise ValidationError(f"File {input_file.filename} must be a text or JSON file")
        
        return True
    
    def start_research_job(self, input_files: List) -> JobResult:
        """
        Start research questions job with uploaded files or latest extraction
        
        Args:
            input_files: List of uploaded input files from Flask request
            
        Returns:
            JobResult: Result of the operation with task details
        """
        return self.start_job(input_files)