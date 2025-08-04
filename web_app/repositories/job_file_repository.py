"""
Repository for job file operations - handles file uploads and downloads
"""
import os
import tempfile
from pathlib import Path

from web_app.database.models import JobFile
from web_app.repositories.base_repository import ModelRepository


class JobFileRepository(ModelRepository[JobFile]):
    """Repository for job file operations"""

    def __init__(self, db_session=None):
        """Initialize job file repository"""
        super().__init__(JobFile, db_session)

    def save_uploaded_file(self, file, task_id, job_type, file_type):
        """Save uploaded file to database"""
        if not file or file.filename == '':
            return None

        def _save_uploaded():
            # Read file data (this could raise OSError)
            file_data = file.read()

            job_file = self.create(
                filename=file.filename,
                content_type=file.content_type or 'application/octet-stream',
                file_size=len(file_data),
                file_data=file_data,
                task_id=task_id,
                job_type=job_type,
                file_type=file_type
            )

            self.logger.info(f"Saved uploaded file: {file.filename} for task {task_id}")
            return job_file.id

        try:
            return self.safe_operation(_save_uploaded, f"save uploaded file {file.filename}")
        except OSError as e:
            self.logger.error(f"IO error reading uploaded file: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Invalid file data: {e}")
            return None

    def save_result_file(self, filename, content, content_type, task_id, job_type):
        """Save result file to database"""
        def _save_result():
            if isinstance(content, str):
                file_data = content.encode('utf-8')
            elif isinstance(content, bytes):
                file_data = content
            else:
                raise ValueError(f"Invalid content type: {type(content)}")

            job_file = self.create(
                filename=filename,
                content_type=content_type,
                file_size=len(file_data),
                file_data=file_data,
                task_id=task_id,
                job_type=job_type,
                file_type='output'
            )

            self.logger.info(f"Saved result file: {filename} for task {task_id}")
            return job_file.id

        try:
            return self.safe_operation(_save_result, f"save result file {filename}")
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid content for result file: {e}")
            return None
        except UnicodeEncodeError as e:
            self.logger.error(f"Encoding error for result file: {e}")
            return None

    def get_file_by_id(self, file_id):
        """Get file by ID"""
        return self.get_by_id(file_id)

    def get_files_by_task_id(self, task_id, file_type=None):
        """Get all files for a task"""
        def _get_files():
            query = JobFile.query.filter_by(task_id=task_id)
            if file_type:
                query = query.filter_by(file_type=file_type)
            return query.all()

        return self.safe_query(_get_files, f"get files for task {task_id}")

    def create_temp_file_from_upload(self, file_id):
        """Create a temporary file from uploaded file data"""
        temp_fd = None
        temp_path = None

        try:
            job_file = self.get_file_by_id(file_id)
            if not job_file:
                return None

            # Create temporary file
            suffix = Path(job_file.filename).suffix
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)

            with os.fdopen(temp_fd, 'wb') as f:
                f.write(job_file.file_data)

            temp_fd = None  # File descriptor is now closed

            self.logger.info(f"Created temp file: {temp_path} from {job_file.filename}")
            return temp_path

        except OSError as e:
            self.logger.error(f"OS error creating temp file from upload {file_id}: {e}")
            if temp_fd:
                os.close(temp_fd)
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

    def create_temp_files_from_uploads(self, task_id, file_type='input'):
        """Create temporary files from all uploaded files for a task"""
        try:
            job_files = self.get_files_by_task_id(task_id, file_type)
            temp_files = []

            for job_file in job_files:
                temp_path = self.create_temp_file_from_upload(job_file.id)
                if temp_path:
                    temp_files.append(temp_path)

            # Sort files by filename for proper ordering (001.pdf, 002.pdf, etc.)
            temp_files.sort(key=lambda x: Path(x).name)

            return temp_files

        except OSError as e:
            self.logger.error(f"Error creating temp files for task {task_id}: {e}")
            return []

    def cleanup_temp_files(self, temp_files):
        """Clean up temporary files"""
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except OSError as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
            except PermissionError as e:
                self.logger.warning(f"Permission denied cleaning up temp file {temp_file}: {e}")

    def get_download_file(self, task_id, job_type):
        """Get the primary download file for a completed job"""
        def _get_download():
            # Get output files for this task
            output_files = self.get_files_by_task_id(task_id, 'output')

            if not output_files:
                return None

            # Return the first output file (or we could implement priority logic)
            return output_files[0]

        return self.safe_query(_get_download, f"get download file for task {task_id}")
