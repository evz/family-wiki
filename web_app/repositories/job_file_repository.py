"""
Repository for job file operations - handles file uploads and downloads
"""
import os
import tempfile
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from web_app.database import db
from web_app.database.models import JobFile
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class JobFileRepository:
    """Repository for job file operations"""

    def save_uploaded_file(self, file, task_id, job_type, file_type):
        """Save uploaded file to database"""
        if not file or file.filename == '':
            return None

        try:
            # Read file data
            file_data = file.read()

            job_file = JobFile(
                filename=file.filename,
                content_type=file.content_type or 'application/octet-stream',
                file_size=len(file_data),
                file_data=file_data,
                task_id=task_id,
                job_type=job_type,
                file_type=file_type
            )

            db.session.add(job_file)
            db.session.commit()

            logger.info(f"Saved uploaded file: {file.filename} for task {task_id}")
            return job_file.id

        except SQLAlchemyError as e:
            logger.error(f"Database error saving uploaded file: {e}")
            db.session.rollback()
            return None
        except OSError as e:
            logger.error(f"IO error reading uploaded file: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid file data: {e}")
            return None

    def save_result_file(self, filename, content, content_type, task_id, job_type):
        """Save result file to database"""
        try:
            if isinstance(content, str):
                file_data = content.encode('utf-8')
            elif isinstance(content, bytes):
                file_data = content
            else:
                raise ValueError(f"Invalid content type: {type(content)}")

            job_file = JobFile(
                filename=filename,
                content_type=content_type,
                file_size=len(file_data),
                file_data=file_data,
                task_id=task_id,
                job_type=job_type,
                file_type='output'
            )

            db.session.add(job_file)
            db.session.commit()

            logger.info(f"Saved result file: {filename} for task {task_id}")
            return job_file.id

        except SQLAlchemyError as e:
            logger.error(f"Database error saving result file: {e}")
            db.session.rollback()
            return None
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid content for result file: {e}")
            return None
        except UnicodeEncodeError as e:
            logger.error(f"Encoding error for result file: {e}")
            return None

    def get_file_by_id(self, file_id):
        """Get file by ID"""
        try:
            return db.session.get(JobFile, file_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error getting file by ID {file_id}: {e}")
            return None

    def get_files_by_task_id(self, task_id, file_type=None):
        """Get all files for a task"""
        try:
            query = JobFile.query.filter_by(task_id=task_id)
            if file_type:
                query = query.filter_by(file_type=file_type)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting files for task {task_id}: {e}")
            return []

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

            logger.info(f"Created temp file: {temp_path} from {job_file.filename}")
            return temp_path

        except OSError as e:
            logger.error(f"OS error creating temp file from upload {file_id}: {e}")
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
            logger.error(f"Error creating temp files for task {task_id}: {e}")
            return []

    def cleanup_temp_files(self, temp_files):
        """Clean up temporary files"""
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except OSError as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
            except PermissionError as e:
                logger.warning(f"Permission denied cleaning up temp file {temp_file}: {e}")

    def get_download_file(self, task_id, job_type):
        """Get the primary download file for a completed job"""
        try:
            # Get output files for this task
            output_files = self.get_files_by_task_id(task_id, 'output')

            if not output_files:
                return None

            # Return the first output file (or we could implement priority logic)
            return output_files[0]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting download file for task {task_id}: {e}")
            return None
