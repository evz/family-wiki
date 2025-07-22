"""
Tests for JobFileRepository
"""
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from web_app.database import db
from web_app.database.models import JobFile
from web_app.repositories.job_file_repository import JobFileRepository


class TestJobFileRepository:
    """Test JobFileRepository functionality"""

    @pytest.fixture
    def repository(self):
        """Create repository instance"""
        return JobFileRepository()

    @pytest.fixture
    def mock_file(self):
        """Create mock uploaded file"""
        file = Mock()
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.read.return_value = b"test file content"
        return file

    @pytest.fixture
    def sample_job_file(self, app):
        """Create sample JobFile in database"""
        job_file = JobFile(
            filename="sample.txt",
            content_type="text/plain",
            file_size=12,
            file_data=b"sample data",
            task_id="test-task-123",
            job_type="ocr",
            file_type="input"
        )
        db.session.add(job_file)
        db.session.commit()
        return job_file

    def test_save_uploaded_file_success(self, repository, mock_file, app):
        """Test successful file upload save"""
        file_id = repository.save_uploaded_file(
            mock_file,
            "task-123",
            "ocr",
            "input"
        )

        assert file_id is not None

        # Verify file was saved to database
        job_file = JobFile.query.get(file_id)
        assert job_file is not None
        assert job_file.filename == "test.pdf"
        assert job_file.content_type == "application/pdf"
        assert job_file.file_size == 17
        assert job_file.file_data == b"test file content"
        assert job_file.task_id == "task-123"
        assert job_file.job_type == "ocr"
        assert job_file.file_type == "input"

    def test_save_uploaded_file_empty_file(self, repository, app):
        """Test saving empty file returns None"""
        empty_file = Mock()
        empty_file.filename = ""

        result = repository.save_uploaded_file(empty_file, "task-123", "ocr", "input")
        assert result is None

    def test_save_uploaded_file_no_file(self, repository, app):
        """Test saving None file returns None"""
        result = repository.save_uploaded_file(None, "task-123", "ocr", "input")
        assert result is None

    def test_save_uploaded_file_no_content_type(self, repository, app):
        """Test file upload with no content type uses default"""
        file = Mock()
        file.filename = "test.txt"
        file.content_type = None
        file.read.return_value = b"test content"

        file_id = repository.save_uploaded_file(file, "task-123", "ocr", "input")

        job_file = JobFile.query.get(file_id)
        assert job_file.content_type == "application/octet-stream"

    @patch('web_app.repositories.job_file_repository.db.session')
    def test_save_uploaded_file_database_error(self, mock_session, repository, mock_file, app):
        """Test database error during file save"""
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        result = repository.save_uploaded_file(mock_file, "task-123", "ocr", "input")

        assert result is None
        mock_session.rollback.assert_called_once()

    def test_save_uploaded_file_read_error(self, repository, app):
        """Test file read error during upload"""
        file = Mock()
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.read.side_effect = OSError("Read error")

        result = repository.save_uploaded_file(file, "task-123", "ocr", "input")
        assert result is None

    def test_save_result_file_string_content(self, repository, app):
        """Test saving result file with string content"""
        file_id = repository.save_result_file(
            "result.txt",
            "test result content",
            "text/plain",
            "task-123",
            "extraction"
        )

        assert file_id is not None

        job_file = JobFile.query.get(file_id)
        assert job_file.filename == "result.txt"
        assert job_file.content_type == "text/plain"
        assert job_file.file_data == b"test result content"
        assert job_file.file_type == "output"

    def test_save_result_file_bytes_content(self, repository, app):
        """Test saving result file with bytes content"""

        content = b"binary result data"
        file_id = repository.save_result_file(
            "result.bin",
            content,
            "application/octet-stream",
            "task-123",
            "extraction"
        )

        job_file = JobFile.query.get(file_id)
        assert job_file.file_data == content

    def test_save_result_file_invalid_content_type(self, repository, app):
        """Test saving result file with invalid content type"""
        result = repository.save_result_file(
            "result.txt",
            123,  # Invalid content type
            "text/plain",
            "task-123",
            "extraction"
        )

        assert result is None

    @patch('web_app.repositories.job_file_repository.db.session')
    def test_save_result_file_database_error(self, mock_session, repository, app):
        """Test database error during result file save"""
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        result = repository.save_result_file(
            "result.txt", "content", "text/plain", "task-123", "extraction"
        )

        assert result is None
        mock_session.rollback.assert_called_once()

    def test_get_file_by_id_success(self, repository, sample_job_file, app):
        """Test successful file retrieval by ID"""
        result = repository.get_file_by_id(sample_job_file.id)

        assert result is not None
        assert result.id == sample_job_file.id
        assert result.filename == "sample.txt"

    def test_get_file_by_id_not_found(self, repository, app):
        """Test file retrieval with non-existent ID"""
        result = repository.get_file_by_id(99999)
        assert result is None

    @patch('web_app.repositories.job_file_repository.JobFile.query')
    def test_get_file_by_id_database_error(self, mock_query, repository, app):
        """Test database error during file retrieval"""
        mock_query.get.side_effect = SQLAlchemyError("Database error")

        result = repository.get_file_by_id(1)
        assert result is None

    def test_get_files_by_task_id_success(self, repository, sample_job_file, app):
        """Test successful file retrieval by task ID"""
        files = repository.get_files_by_task_id("test-task-123")

        assert len(files) == 1
        assert files[0].id == sample_job_file.id

    def test_get_files_by_task_id_with_file_type(self, repository, app):
        """Test file retrieval by task ID and file type"""
        from web_app.database import db

        # Create files with different types
        job_file1 = JobFile(
            filename="input.pdf", content_type="application/pdf", file_size=10,
            file_data=b"input", task_id="task-123", job_type="ocr", file_type="input"
        )
        job_file2 = JobFile(
            filename="output.txt", content_type="text/plain", file_size=10,
            file_data=b"output", task_id="task-123", job_type="ocr", file_type="output"
        )
        db.session.add_all([job_file1, job_file2])
        db.session.commit()

        input_files = repository.get_files_by_task_id("task-123", "input")
        output_files = repository.get_files_by_task_id("task-123", "output")

        assert len(input_files) == 1
        assert len(output_files) == 1
        assert input_files[0].file_type == "input"
        assert output_files[0].file_type == "output"

    def test_get_files_by_task_id_no_files(self, repository, app):
        """Test file retrieval for non-existent task"""
        files = repository.get_files_by_task_id("non-existent-task")
        assert files == []

    @patch('web_app.repositories.job_file_repository.JobFile.query')
    def test_get_files_by_task_id_database_error(self, mock_query, repository, app):
        """Test database error during files retrieval"""
        from sqlalchemy.exc import SQLAlchemyError

        mock_query.filter_by.return_value.all.side_effect = SQLAlchemyError("Database error")

        result = repository.get_files_by_task_id("task-123")
        assert result == []

    @patch('tempfile.mkstemp')
    @patch('os.fdopen')
    def test_create_temp_file_from_upload_success(self, mock_fdopen, mock_mkstemp, repository, sample_job_file, app):
        """Test successful temporary file creation"""
        # Mock tempfile creation
        mock_mkstemp.return_value = (5, "/tmp/test123.txt")
        mock_file = Mock()
        mock_fdopen.return_value.__enter__.return_value = mock_file

        temp_path = repository.create_temp_file_from_upload(sample_job_file.id)

        assert temp_path == "/tmp/test123.txt"
        mock_mkstemp.assert_called_once_with(suffix=".txt")
        mock_file.write.assert_called_once_with(b"sample data")

    def test_create_temp_file_from_upload_file_not_found(self, repository, app):
        """Test temp file creation with non-existent file"""
        result = repository.create_temp_file_from_upload(99999)
        assert result is None

    @patch('tempfile.mkstemp')
    def test_create_temp_file_from_upload_os_error(self, mock_mkstemp, repository, sample_job_file, app):
        """Test OS error during temp file creation"""
        mock_mkstemp.side_effect = OSError("Permission denied")

        result = repository.create_temp_file_from_upload(sample_job_file.id)
        assert result is None

    def test_create_temp_files_from_uploads_success(self, repository, app):
        """Test creating multiple temp files from uploads"""
        from web_app.database import db

        # Create multiple files for the same task
        job_files = [
            JobFile(
                filename=f"file{i}.pdf", content_type="application/pdf", file_size=10,
                file_data=f"content{i}".encode(), task_id="task-123",
                job_type="ocr", file_type="input"
            )
            for i in range(3)
        ]
        db.session.add_all(job_files)
        db.session.commit()

        with patch.object(repository, 'create_temp_file_from_upload') as mock_create:
            mock_create.side_effect = ["/tmp/file0.pdf", "/tmp/file1.pdf", "/tmp/file2.pdf"]

            temp_files = repository.create_temp_files_from_uploads("task-123", "input")

            assert len(temp_files) == 3
            assert mock_create.call_count == 3

    def test_create_temp_files_from_uploads_no_files(self, repository, app):
        """Test creating temp files when no files exist"""
        result = repository.create_temp_files_from_uploads("non-existent-task")
        assert result == []

    @patch('os.path.exists')
    @patch('os.unlink')
    def test_cleanup_temp_files_success(self, mock_unlink, mock_exists, repository):
        """Test successful temp file cleanup"""
        mock_exists.return_value = True
        temp_files = ["/tmp/file1.pdf", "/tmp/file2.pdf"]

        repository.cleanup_temp_files(temp_files)

        assert mock_unlink.call_count == 2
        mock_unlink.assert_any_call("/tmp/file1.pdf")
        mock_unlink.assert_any_call("/tmp/file2.pdf")

    @patch('os.path.exists')
    @patch('os.unlink')
    def test_cleanup_temp_files_os_error(self, mock_unlink, mock_exists, repository):
        """Test temp file cleanup with OS error"""
        mock_exists.return_value = True
        mock_unlink.side_effect = OSError("Permission denied")

        # Should not raise exception
        repository.cleanup_temp_files(["/tmp/file1.pdf"])

    @patch('os.path.exists')
    def test_cleanup_temp_files_non_existent(self, mock_exists, repository):
        """Test cleanup of non-existent temp files"""
        mock_exists.return_value = False

        # Should not attempt to unlink
        with patch('os.unlink') as mock_unlink:
            repository.cleanup_temp_files(["/tmp/non-existent.pdf"])
            mock_unlink.assert_not_called()

    def test_get_download_file_success(self, repository, app):
        """Test successful download file retrieval"""
        from web_app.database import db

        # Create output file
        job_file = JobFile(
            filename="output.txt", content_type="text/plain", file_size=10,
            file_data=b"output", task_id="task-123", job_type="ocr", file_type="output"
        )
        db.session.add(job_file)
        db.session.commit()

        result = repository.get_download_file("task-123", "ocr")

        assert result is not None
        assert result.id == job_file.id
        assert result.file_type == "output"

    def test_get_download_file_no_output_files(self, repository, app):
        """Test download file retrieval when no output files exist"""
        result = repository.get_download_file("task-123", "ocr")
        assert result is None

    def test_get_download_file_multiple_outputs(self, repository, app):
        """Test download file retrieval with multiple output files"""
        from web_app.database import db

        # Create multiple output files
        job_files = [
            JobFile(
                filename=f"output{i}.txt", content_type="text/plain", file_size=10,
                file_data=f"output{i}".encode(), task_id="task-123",
                job_type="ocr", file_type="output"
            )
            for i in range(2)
        ]
        db.session.add_all(job_files)
        db.session.commit()

        result = repository.get_download_file("task-123", "ocr")

        # Should return the first output file
        assert result is not None
        assert result.filename == "output0.txt"

    def test_get_download_file_database_error(self, repository, app):
        """Test database error during download file retrieval"""
        # Mock the get_files_by_task_id method to raise an exception
        with patch.object(repository, 'get_files_by_task_id') as mock_get_files:
            mock_get_files.side_effect = SQLAlchemyError("Database error")

            result = repository.get_download_file("task-123", "ocr")
            assert result is None
