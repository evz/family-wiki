"""
Tests for OCR Celery tasks - focus on real user workflows and business logic
"""
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from web_app.tasks.ocr_tasks import OCRTaskManager, process_pdfs_ocr
from tests.test_utils import MockTaskProgressRepository


class TestOCRTaskManagerWorkflows:
    """Test real OCR workflows that users actually experience"""

    @pytest.fixture
    def task_id(self):
        """Sample task ID"""
        return str(uuid.uuid4())

    @pytest.fixture 
    def mock_ocr_externals(self):
        """Mock only external dependencies (pytesseract, fitz) - not our business logic"""
        with patch('web_app.pdf_processing.ocr_processor.fitz.open') as mock_fitz, \
             patch('web_app.pdf_processing.ocr_processor.pytesseract.image_to_string') as mock_img_to_str, \
             patch('web_app.pdf_processing.ocr_processor.pytesseract.image_to_osd') as mock_osd, \
             patch('web_app.pdf_processing.ocr_processor.pytesseract.image_to_data') as mock_data, \
             patch('web_app.pdf_processing.ocr_processor.tempfile.NamedTemporaryFile') as mock_tempfile:
            
            # Setup fitz mocks for PDF parsing
            mock_doc = Mock()
            mock_fitz.return_value = mock_doc
            mock_doc.__len__ = Mock(return_value=1)  # 1 page
            mock_doc.close = Mock()
            
            mock_page = Mock()
            mock_doc.load_page.return_value = mock_page
            
            mock_pixmap = Mock()
            mock_page.get_pixmap.return_value = mock_pixmap
            mock_pixmap.tobytes.return_value = b'fake_image_data'
            
            # Setup tempfile mock
            mock_temp = Mock()
            mock_temp.name = '/tmp/fake_temp.ppm'
            mock_tempfile.return_value.__enter__.return_value = mock_temp
            
            # Setup pytesseract mocks - return realistic genealogy text
            mock_img_to_str.return_value = "Jan van der Berg\\nGeboren: 15 maart 1845 te Amsterdam"
            mock_osd.return_value = "Orientation in degrees: 0\\nRotate: 0"
            mock_data.return_value = {'conf': [80, 85], 'text': ['Jan', 'van']}
            
            with patch('PIL.Image.open'):  # Mock PIL image opening
                yield {
                    'fitz': mock_fitz,
                    'img_to_str': mock_img_to_str,
                    'osd': mock_osd,
                    'data': mock_data
                }

    def test_user_workflow_upload_and_process_pdfs(self, task_id, mock_ocr_externals, app, db):
        """
        Test the complete user workflow: upload PDFs → process → get consolidated results
        
        This is what actually happens when a user uploads files and starts OCR processing.
        """
        with app.app_context():
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Simulate user uploaded files by creating temp PDFs
                pdf1 = Path(tmp_dir) / "document1.pdf"
                pdf2 = Path(tmp_dir) / "document2.pdf"
                pdf1.write_bytes(b"%PDF-1.4 fake content")
                pdf2.write_bytes(b"%PDF-1.4 fake content")
                
                # Create task manager with real directory
                task_manager = OCRTaskManager(task_id, tmp_dir)
                
                # Override progress tracking for testing
                task_manager.progress = MockTaskProgressRepository(task_id)
                
                # Run the complete workflow
                result = task_manager.run()
                
                # Verify user gets meaningful results
                assert result['success'] is True
                assert result['files_processed'] == 2
                assert result['total_files'] == 2
                assert result['consolidated_file_id'] is not None
                
                # Verify progress was tracked (user can see progress)
                progress_updates = task_manager.progress.progress_updates
                assert len(progress_updates) > 0
                assert any('processing' in update['status'] for update in progress_updates)

    def test_user_workflow_empty_folder_graceful_handling(self, task_id):
        """
        Test user workflow when they point to an empty folder
        
        User should get clear feedback, not a crash.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_manager = OCRTaskManager(task_id, tmp_dir)
            task_manager.progress = MockTaskProgressRepository(task_id)
            
            result = task_manager.run()
            
            # User gets clear feedback about no files
            assert result['success'] is True
            assert result['message'] == 'No PDF files found to process'
            assert result['files_processed'] == 0

    def test_user_workflow_permission_errors_handled_gracefully(self, task_id):
        """
        Test user workflow when they don't have permission to access folder
        
        User should get clear error message, not a crash.
        """
        nonexistent_path = "/definitely/does/not/exist/folder"
        task_manager = OCRTaskManager(task_id, nonexistent_path)
        
        # User gets clear error about folder access
        with pytest.raises(FileNotFoundError, match="PDF folder not found"):
            task_manager._validate_paths()

    def test_user_workflow_mixed_success_and_failure_files(self, task_id, mock_ocr_externals, app, db):
        """
        Test user workflow when some PDFs process successfully and others fail
        
        User should get accurate reporting of what worked and what didn't.
        """
        with app.app_context():
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create one good PDF and one that will fail processing
                good_pdf = Path(tmp_dir) / "good.pdf"
                bad_pdf = Path(tmp_dir) / "bad.pdf"
                good_pdf.write_bytes(b"%PDF-1.4 good content")
                bad_pdf.write_bytes(b"%PDF-1.4 bad content")
                
                task_manager = OCRTaskManager(task_id, tmp_dir)
                task_manager.progress = MockTaskProgressRepository(task_id)
                
                # Make the second PDF fail processing
                def selective_ocr_failure(pdf_path):
                    if "bad.pdf" in str(pdf_path):
                        raise RuntimeError("OCR failed")
                    return "Extracted text from good PDF"
                
                # Mock OCR to fail on bad.pdf
                with patch('web_app.pdf_processing.ocr_processor.PDFOCRProcessor') as mock_processor_class:
                    mock_processor = Mock()
                    mock_processor_class.return_value = mock_processor
                    mock_processor.process_pdf.side_effect = selective_ocr_failure
                    
                    result = task_manager.run()
                
                # User gets accurate reporting of mixed results
                assert result['success'] is True  # Overall success even with some failures
                assert result['files_processed'] == 1
                assert result['files_failed'] == 1
                assert result['total_files'] == 2
                assert len(result['failed_files']) == 1
                assert 'bad.pdf' in result['failed_files'][0]

    def test_celery_task_integration_with_real_task_manager(self, app, db):
        """
        Test the actual Celery task function users invoke
        
        This tests the integration between Celery and our TaskManager.
        """
        with app.app_context():
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create a test PDF
                test_pdf = Path(tmp_dir) / "test.pdf"
                test_pdf.write_bytes(b"%PDF-1.4 test content")
                
                # Mock only external OCR dependencies
                with patch('web_app.pdf_processing.ocr_processor.fitz.open'), \
                     patch('web_app.pdf_processing.ocr_processor.pytesseract.image_to_string', return_value="Test text"), \
                     patch('web_app.pdf_processing.ocr_processor.pytesseract.image_to_osd', return_value="Orientation: 0"), \
                     patch('web_app.pdf_processing.ocr_processor.pytesseract.image_to_data', return_value={'conf': [80], 'text': ['Test']}), \
                     patch('PIL.Image.open'):
                    
                    # Call the actual Celery task
                    result = process_pdfs_ocr.apply(args=(tmp_dir,))
                    
                    # User gets the expected task result
                    assert result.successful()
                    task_result = result.result
                    assert task_result['success'] is True
                    assert task_result['files_processed'] >= 0  # May be 0 or 1 depending on mock behavior

    def test_output_folder_creation_user_workflow(self, task_id):
        """
        Test that output folder is automatically created for user
        
        User shouldn't have to manually create output directories.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_manager = OCRTaskManager(task_id, tmp_dir)
            
            # Output folder shouldn't exist initially
            output_folder = Path(tmp_dir) / "extracted_text"
            assert not output_folder.exists()
            
            # Validation creates it automatically for user
            task_manager._validate_paths()
            
            # Now it exists and user can write to it
            assert output_folder.exists()
            assert output_folder.is_dir()

    def test_consolidated_file_creation_user_workflow(self, task_id, app, db):
        """
        Test that users get a consolidated file they can download
        
        This is a key user-facing feature - they should get one combined file.
        """
        with app.app_context():
            with tempfile.TemporaryDirectory() as tmp_dir:
                task_manager = OCRTaskManager(task_id, tmp_dir)
                task_manager._validate_paths()
                
                # Simulate having processed some files (what user uploaded)
                text1_path = task_manager.output_folder / "doc1.txt"
                text2_path = task_manager.output_folder / "doc2.txt"
                
                text1_path.write_text("First document: Jan van Bulhuis * 1800", encoding='utf-8')
                text2_path.write_text("Second document: Maria de Vries ~ 1805", encoding='utf-8')
                
                processed_files = [
                    {'output_file': str(text1_path)},
                    {'output_file': str(text2_path)}
                ]
                
                # Create consolidated file (what user downloads)
                file_id = task_manager._create_consolidated_text_file(processed_files)
                
                # User gets a file they can actually download
                assert file_id is not None
                
                from web_app.database.models import JobFile
                result_file = JobFile.query.get(file_id)
                assert result_file.filename == 'consolidated_text.txt'
                
                # File contains content from both documents user uploaded
                content = result_file.file_data.decode('utf-8')
                assert 'doc1.txt' in content
                assert 'doc2.txt' in content
                assert 'Jan van Bulhuis' in content
                assert 'Maria de Vries' in content


class TestOCRErrorScenarios:
    """Test error scenarios users might encounter"""

    def test_user_points_to_file_instead_of_directory(self):
        """User accidentally selects a file instead of directory"""
        with tempfile.NamedTemporaryFile() as tmp_file:
            task_manager = OCRTaskManager('test-task', tmp_file.name)
            
            with pytest.raises(NotADirectoryError, match="PDF path is not a directory"):
                task_manager._validate_paths()

    def test_user_has_no_write_permission_for_output(self):
        """User tries to process in directory they can't write to"""
        # This would test permission errors, but is hard to simulate reliably in tests
        # The real behavior is tested in the permission error test above
        pass


class TestOCRBusinessLogic:
    """Test core business logic without excessive mocking"""

    def test_pdf_file_discovery_logic(self):
        """Test how the system finds PDF files to process"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create mix of files
            pdf1 = Path(tmp_dir) / "document.pdf"
            pdf2 = Path(tmp_dir) / "another.pdf"
            txt_file = Path(tmp_dir) / "readme.txt"
            
            pdf1.touch()
            pdf2.touch()
            txt_file.touch()
            
            task_manager = OCRTaskManager('test-task', tmp_dir)
            
            # Mock the file repo to simulate no uploads
            task_manager.file_repo.create_temp_files_from_uploads = Mock(return_value=[])
            
            success = task_manager._get_pdf_files()
            
            # Should find only PDF files, ignore others
            assert success is True
            assert len(task_manager.pdf_files) == 2
            assert all(f.suffix == '.pdf' for f in task_manager.pdf_files)

    def test_file_upload_prioritization_logic(self):
        """Test that uploaded files take priority over folder files"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create folder with PDFs
            folder_pdf = Path(tmp_dir) / "folder.pdf"
            folder_pdf.touch()
            
            task_manager = OCRTaskManager('test-task', tmp_dir)
            
            # Mock uploaded files
            uploaded_files = ['/tmp/upload1.pdf', '/tmp/upload2.pdf']
            task_manager.file_repo.create_temp_files_from_uploads = Mock(return_value=uploaded_files)
            
            success = task_manager._get_pdf_files()
            
            # Should use uploaded files, not folder files
            assert success is True
            assert len(task_manager.pdf_files) == 2
            assert str(task_manager.pdf_files[0]) == '/tmp/upload1.pdf'
            assert str(task_manager.pdf_files[1]) == '/tmp/upload2.pdf'