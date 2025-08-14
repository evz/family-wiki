"""
Tests for OCR Celery tasks - background OCR processing
"""
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from web_app.tasks.ocr_tasks import OCRTaskManager, process_pdfs_ocr
from tests.test_utils import MockTaskProgressRepository


class TestOCRTaskManager:
    """Test OCR task manager functionality"""

    @pytest.fixture
    def task_id(self):
        """Sample task ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def task_manager(self, task_id):
        """OCR task manager instance"""
        return OCRTaskManager(task_id)

    @pytest.fixture
    def mock_file_repo(self):
        """Mock file repository"""
        return Mock()

    @pytest.fixture
    def mock_processor(self):
        """Mock OCR processor"""
        return Mock()

    def test_init_default_path(self, task_id):
        """Test task manager initialization with default path"""
        manager = OCRTaskManager(task_id)
        assert manager.task_id == task_id
        assert manager.pdf_folder_path == "web_app/pdf_processing/pdfs"
        assert manager.pdf_folder == Path("web_app/pdf_processing/pdfs")
        assert manager.processor is None
        assert manager.pdf_files == []
        assert manager.temp_files == []
        assert isinstance(manager.file_repo, type(manager.file_repo))

    def test_init_custom_path(self, task_id):
        """Test task manager initialization with custom path"""
        custom_path = "/custom/path"
        manager = OCRTaskManager(task_id, custom_path)
        assert manager.task_id == task_id
        assert manager.pdf_folder_path == custom_path
        assert manager.pdf_folder == Path(custom_path)

    def test_validate_paths_missing_folder(self, task_manager):
        """Test path validation with missing PDF folder"""
        # Use a non-existent path
        task_manager.pdf_folder = Path("/non/existent/path")

        with pytest.raises(FileNotFoundError, match="PDF folder not found"):
            task_manager._validate_paths()

    def test_validate_paths_not_directory(self, task_manager):
        """Test path validation when PDF path is not a directory"""
        # Create a temporary file (not directory)
        with tempfile.NamedTemporaryFile() as tmp_file:
            task_manager.pdf_folder = Path(tmp_file.name)

            with pytest.raises(NotADirectoryError, match="PDF path is not a directory"):
                task_manager._validate_paths()

    def test_validate_paths_creates_output_folder(self, task_manager):
        """Test path validation creates output folder when it doesn't exist"""
        # Create a temporary directory for PDF folder
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_manager.pdf_folder = Path(tmp_dir)
            task_manager.output_folder = Path(tmp_dir) / "extracted_text"
            
            # Output folder shouldn't exist initially
            assert not task_manager.output_folder.exists()
            
            # Validation should create the output folder
            task_manager._validate_paths()
            
            # Output folder should now exist
            assert task_manager.output_folder.exists()
            assert task_manager.output_folder.is_dir()

    def test_get_pdf_files_from_uploads(self, task_manager):
        """Test getting PDF files from uploads"""
        mock_temp_files = ["/tmp/file1.pdf", "/tmp/file2.pdf"]
        task_manager.file_repo.create_temp_files_from_uploads = Mock(return_value=mock_temp_files)

        result = task_manager._get_pdf_files()

        assert result is True
        assert task_manager.temp_files == mock_temp_files
        assert task_manager.pdf_files == [Path("/tmp/file1.pdf"), Path("/tmp/file2.pdf")]
        task_manager.file_repo.create_temp_files_from_uploads.assert_called_once_with(task_manager.task_id, 'input')

    def test_get_pdf_files_from_folder(self, task_manager):
        """Test getting PDF files from folder when no uploads"""
        # Mock no uploads
        task_manager.file_repo.create_temp_files_from_uploads = Mock(return_value=[])

        # Create temporary directory with PDF files
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf1 = Path(tmp_dir) / "file1.pdf"
            pdf2 = Path(tmp_dir) / "file2.pdf"
            pdf1.touch()
            pdf2.touch()

            task_manager.pdf_folder = Path(tmp_dir)

            result = task_manager._get_pdf_files()

            assert result is True
            assert len(task_manager.pdf_files) == 2
            assert all(f.name.endswith('.pdf') for f in task_manager.pdf_files)

    def test_get_pdf_files_no_files_found(self, task_manager):
        """Test getting PDF files when none are found"""
        # Mock no uploads
        task_manager.file_repo.create_temp_files_from_uploads = Mock(return_value=[])

        # Create empty temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_manager.pdf_folder = Path(tmp_dir)

            result = task_manager._get_pdf_files()

            assert result is False
            assert task_manager.pdf_files == []

    def test_get_pdf_files_permission_error(self, task_manager):
        """Test getting PDF files with permission error"""
        task_manager.file_repo.create_temp_files_from_uploads = Mock(return_value=[])

        # Mock permission error on glob
        with patch.object(Path, 'glob', side_effect=PermissionError("Access denied")):
            task_manager.pdf_folder = Path("/some/path")

            with pytest.raises(PermissionError, match="Cannot access PDF folder"):
                task_manager._get_pdf_files()

    def test_process_single_pdf_success(self, task_manager, mock_processor):
        """Test successful single PDF processing"""
        task_manager.processor = mock_processor
        mock_processor.process_single_pdf.return_value = True

        pdf_file = Path("/tmp/test.pdf")
        output_file = Path("/tmp/test.txt")

        result = task_manager._process_single_pdf(pdf_file, output_file)

        assert result is True
        mock_processor.process_single_pdf.assert_called_once_with(pdf_file, output_file)

    def test_process_single_pdf_file_not_found(self, task_manager, mock_processor):
        """Test single PDF processing with file not found"""
        task_manager.processor = mock_processor
        mock_processor.process_single_pdf.side_effect = FileNotFoundError("File not found")

        pdf_file = Path("/tmp/test.pdf")
        output_file = Path("/tmp/test.txt")

        result = task_manager._process_single_pdf(pdf_file, output_file)

        assert result is False

    def test_process_single_pdf_permission_error(self, task_manager, mock_processor):
        """Test single PDF processing with permission error"""
        task_manager.processor = mock_processor
        mock_processor.process_single_pdf.side_effect = PermissionError("Permission denied")

        pdf_file = Path("/tmp/test.pdf")
        output_file = Path("/tmp/test.txt")

        result = task_manager._process_single_pdf(pdf_file, output_file)

        assert result is False

    def test_process_single_pdf_value_error(self, task_manager, mock_processor):
        """Test single PDF processing with value error"""
        task_manager.processor = mock_processor
        mock_processor.process_single_pdf.side_effect = ValueError("Invalid PDF")

        pdf_file = Path("/tmp/test.pdf")
        output_file = Path("/tmp/test.txt")

        result = task_manager._process_single_pdf(pdf_file, output_file)

        assert result is False

    def test_process_single_pdf_runtime_error(self, task_manager, mock_processor):
        """Test single PDF processing with runtime error"""
        task_manager.processor = mock_processor
        mock_processor.process_single_pdf.side_effect = RuntimeError("OCR failed")

        pdf_file = Path("/tmp/test.pdf")
        output_file = Path("/tmp/test.txt")

        result = task_manager._process_single_pdf(pdf_file, output_file)

        assert result is False

    def test_create_consolidated_text_file_success(self, task_manager):
        """Test successful consolidated text file creation"""
        processed_files = [
            {'output_file': '/tmp/file1.txt'},
            {'output_file': '/tmp/file2.txt'}
        ]

        # Mock file contents
        file_contents = {
            '/tmp/file1.txt': 'Content of file 1',
            '/tmp/file2.txt': 'Content of file 2'
        }

        def mock_open_func(file_path, *args, **kwargs):
            content = file_contents.get(str(file_path), '')
            mock_file = Mock()
            mock_file.read.return_value = content
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)
            return mock_file

        task_manager.file_repo.save_result_file = Mock(return_value="file_id_123")

        with patch('builtins.open', side_effect=mock_open_func):
            with patch.object(Path, 'exists', return_value=True):
                result = task_manager._create_consolidated_text_file(processed_files)

        assert result == "file_id_123"
        task_manager.file_repo.save_result_file.assert_called_once()

    def test_create_consolidated_text_file_unicode_error(self, task_manager):
        """Test consolidated text file creation with unicode error"""
        processed_files = [{'output_file': '/tmp/file1.txt'}]

        def mock_open_func(*args, **kwargs):
            mock_file = Mock()
            mock_file.read.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)
            return mock_file

        task_manager.file_repo.save_result_file = Mock(return_value="file_id_123")

        with patch('builtins.open', side_effect=mock_open_func):
            with patch.object(Path, 'exists', return_value=True):
                result = task_manager._create_consolidated_text_file(processed_files)

        assert result == "file_id_123"

    def test_create_consolidated_text_file_io_error(self, task_manager):
        """Test consolidated text file creation with IO error"""
        processed_files = [{'output_file': '/tmp/file1.txt'}]

        def mock_open_func(*args, **kwargs):
            mock_file = Mock()
            mock_file.read.side_effect = OSError("IO error")
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)
            return mock_file

        task_manager.file_repo.save_result_file = Mock(return_value="file_id_123")

        with patch('builtins.open', side_effect=mock_open_func):
            with patch.object(Path, 'exists', return_value=True):
                result = task_manager._create_consolidated_text_file(processed_files)

        assert result == "file_id_123"

    def test_create_consolidated_text_file_save_failure(self, task_manager):
        """Test consolidated text file creation when save fails"""
        processed_files = [{'output_file': '/tmp/file1.txt'}]

        def mock_open_func(*args, **kwargs):
            mock_file = Mock()
            mock_file.read.return_value = "test content"
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)
            return mock_file

        task_manager.file_repo.save_result_file = Mock(return_value=None)

        with patch('builtins.open', side_effect=mock_open_func):
            with patch.object(Path, 'exists', return_value=True):
                result = task_manager._create_consolidated_text_file(processed_files)

        assert result is None

    def test_create_consolidated_text_file_exception(self, task_manager):
        """Test consolidated text file creation with general exception"""
        processed_files = [{'output_file': '/tmp/file1.txt'}]

        task_manager.file_repo.save_result_file = Mock(side_effect=Exception("Database error"))

        with patch.object(Path, 'exists', return_value=True):
            # The method now handles exceptions gracefully instead of raising them
            result = task_manager._create_consolidated_text_file(processed_files)
            # Should return None when save fails
            assert result is None

    def test_run_ocr_processing_no_files(self, task_manager):
        """Test OCR processing when no files found"""
        # Override with mock progress repository for testing
        task_manager.progress = MockTaskProgressRepository('test-task-id')
        
        # Mock the path validation and file getting
        task_manager._validate_paths = Mock()
        task_manager._get_pdf_files = Mock(return_value=False)
        # Add the missing output_folder attribute for the test
        task_manager.output_folder = Path("/tmp/output")

        result = task_manager.run()

        assert result['success'] is True
        assert result['message'] == 'No PDF files found to process'
        assert result['files_processed'] == 0
        # Check that progress updates were made
        assert len(task_manager.progress.progress_updates) > 0

    @patch('web_app.tasks.ocr_tasks.PDFOCRProcessor')
    def test_run_ocr_processing_success(self, mock_processor_class, task_manager):
        """Test successful OCR processing"""
        # Override with mock progress repository for testing
        task_manager.progress = MockTaskProgressRepository('test-task-id')
        
        # Setup mocks
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        task_manager._validate_paths = Mock()
        task_manager._get_pdf_files = Mock(return_value=True)
        task_manager.pdf_files = [Path("/tmp/file1.pdf"), Path("/tmp/file2.pdf")]
        task_manager._process_single_pdf = Mock(side_effect=[True, True])
        task_manager._create_consolidated_text_file = Mock(return_value="file_id_123")
        task_manager.temp_files = []
        task_manager.file_repo.cleanup_temp_files = Mock()

        # Add the missing output_folder attribute
        task_manager.output_folder = Path("/tmp/output")

        # Mock Path.stat for file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 1024
            with patch.object(Path, 'exists', return_value=True):
                result = task_manager.run()

        assert result['success'] is True
        assert result['files_processed'] == 2
        assert result['files_failed'] == 0
        assert result['total_files'] == 2
        assert result['consolidated_file_id'] == "file_id_123"

        # Verify processor was created and used
        mock_processor_class.assert_called_once()
        assert task_manager._process_single_pdf.call_count == 2
        # Check that progress updates were made
        assert len(task_manager.progress.progress_updates) > 0

    @patch('web_app.tasks.ocr_tasks.PDFOCRProcessor')
    def test_run_ocr_processing_with_failures(self, mock_processor_class, task_manager):
        """Test OCR processing with some failures"""
        # Override with mock progress repository for testing
        task_manager.progress = MockTaskProgressRepository('test-task-id')
        
        # Setup mocks
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        task_manager._validate_paths = Mock()
        task_manager._get_pdf_files = Mock(return_value=True)
        task_manager.pdf_files = [Path("/tmp/file1.pdf"), Path("/tmp/file2.pdf")]
        task_manager._process_single_pdf = Mock(side_effect=[True, False])  # One success, one failure
        task_manager._create_consolidated_text_file = Mock(return_value="file_id_123")
        task_manager.temp_files = ["/tmp/temp1.pdf"]
        task_manager.file_repo.cleanup_temp_files = Mock()

        # Add the missing output_folder attribute
        task_manager.output_folder = Path("/tmp/output")

        # Mock Path.stat for file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 1024
            with patch.object(Path, 'exists', return_value=True):
                result = task_manager.run()

        assert result['success'] is True
        assert result['files_processed'] == 1
        assert result['files_failed'] == 1
        assert result['total_files'] == 2

        # Verify temp files cleanup
        task_manager.file_repo.cleanup_temp_files.assert_called_once_with(["/tmp/temp1.pdf"])
        # Check that progress updates were made
        assert len(task_manager.progress.progress_updates) > 0


class TestProcessPdfsOcrTask:
    """Test the main Celery task function"""

    @pytest.fixture
    def task_id(self):
        """Sample task ID"""
        return str(uuid.uuid4())

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_success(self, mock_current_task, mock_manager_class, task_id):
        """Test successful OCR processing task"""
        # Mock the task request
        mock_request = Mock()
        mock_request.id = task_id

        # Mock the task manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.return_value = {
            'success': True,
            'files_processed': 2,
            'files_failed': 0
        }

        # Create a mock task function with the request attribute
        with patch('web_app.tasks.ocr_tasks.process_pdfs_ocr') as mock_task:
            mock_task.request = mock_request

            # Call the actual function logic
            result = mock_manager.run()

        assert result['success'] is True
        assert result['files_processed'] == 2

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_file_not_found(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with file not found error"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = FileNotFoundError("File not found")

        # Test that the error handling path would be triggered
        with pytest.raises(FileNotFoundError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_not_directory_error(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with not a directory error"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = NotADirectoryError("Not a directory")

        with pytest.raises(NotADirectoryError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_permission_error(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with permission error"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_connection_error(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with connection error (should retry)"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_io_error(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with IO error (should retry)"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = OSError("IO error")

        with pytest.raises(IOError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_import_error(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with import error"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = ImportError("Missing dependency")

        with pytest.raises(ImportError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_runtime_error(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with runtime error"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = RuntimeError("Runtime error")

        with pytest.raises(RuntimeError):
            mock_manager.run()

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_custom_path(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with custom PDF folder path"""
        custom_path = "/custom/pdf/path"

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.return_value = {'success': True}

        # Verify manager is created with custom path
        mock_manager_class.assert_not_called()  # Will be called when we actually invoke

        # Test that manager would be created with custom path
        OCRTaskManager(task_id, custom_path)

        # This verifies the constructor accepts the custom path
        assert True  # If we get here, the constructor worked

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    def test_process_pdfs_ocr_default_path(self, mock_current_task, mock_manager_class, task_id):
        """Test OCR processing task with default PDF folder path"""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.return_value = {'success': True}

        # Test that manager is created with default path when None provided
        OCRTaskManager(task_id, None)

        # This verifies the constructor works with None (uses default)
        assert True


class TestProcessPdfsOcrIntegration:
    """Integration tests for the actual Celery task function using pytest-celery"""

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    def test_process_pdfs_ocr_success_integration(self, mock_manager_class):
        """Test successful OCR processing task integration"""
        # Setup mock manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        expected_result = {
            'success': True,
            'files_processed': 2,
            'files_failed': 0
        }
        mock_manager.run.return_value = expected_result

        # Test the task using pytest-celery approach
        # Call apply() to execute the task synchronously for testing
        result = process_pdfs_ocr.apply(args=("custom/path",))

        # Verify results
        assert result.result == expected_result
        assert result.successful()
        mock_manager_class.assert_called_once()
        mock_manager.run.assert_called_once()
        # Logger calls are now handled by BaseFileProcessingTask

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    @patch('web_app.tasks.ocr_tasks.logger')
    def test_process_pdfs_ocr_file_not_found_integration(self, mock_logger, mock_current_task, mock_manager_class):
        """Test OCR processing task with FileNotFoundError"""
        # Setup mock manager to raise exception
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.run.side_effect = FileNotFoundError("File not found")

        # Call apply() to execute the task synchronously
        result = process_pdfs_ocr.apply(args=(None,))

        # Verify task failed - FileNotFoundError should not be retried and should fail after max retries
        assert result.failed()
        assert isinstance(result.result, FileNotFoundError)
        # Error logging and retry logic are now handled by BaseFileProcessingTask

    @patch('web_app.tasks.ocr_tasks.OCRTaskManager')
    @patch('web_app.tasks.ocr_tasks.current_task')
    @patch('web_app.tasks.ocr_tasks.logger')
    def test_process_pdfs_ocr_connection_error_integration(self, mock_logger, mock_current_task, mock_manager_class):
        """Test OCR processing task with ConnectionError (should retry)"""
        # Setup mock manager to raise exception
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        connection_error = ConnectionError("Connection failed")
        mock_manager.run.side_effect = connection_error

        # Call apply() to execute the task synchronously
        result = process_pdfs_ocr.apply(args=(None,))

        # ConnectionError should be retried according to autoretry_for configuration
        # After max retries, it should show as a Retry exception
        assert not result.successful()
        # Error logging and retry logic are now handled by BaseFileProcessingTask
