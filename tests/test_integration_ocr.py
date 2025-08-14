"""
Integration tests for OCR workflow - real end-to-end testing

This test exercises the complete OCR workflow:
1. HTTP POST to /ocr/start route with real files
2. Real task execution (synchronous due to CELERY_TASK_ALWAYS_EAGER)
3. Real file processing through TaskManager
4. Real database storage of results
5. Real file system operations with temp directories

Only external OCR processor is mocked - everything else runs real code paths.
"""
import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from flask import url_for
from io import BytesIO
from werkzeug.datastructures import FileStorage

from web_app.database.models import JobFile
from web_app.services.ocr_service import OCRService
from web_app.services.file_job_service import JobResult
from web_app.tasks.ocr_tasks import OCRTaskManager


class TestOCRWorkflowIntegration:
    """Test complete OCR workflow from HTTP request to database results"""

    @pytest.fixture
    def fake_pdf_file(self):
        """Create a fake PDF file for testing"""
        fake_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF"
        return (io.BytesIO(fake_pdf_content), "test_document.pdf")

    @pytest.fixture 
    def mock_ocr_processor(self):
        """Mock only the OCR processor (external dependency)"""
        with patch('web_app.pdf_processing.ocr_processor.PDFOCRProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            # Simulate successful OCR extraction by writing real text to output file
            def fake_process_pdf(input_file, output_file):
                # Write realistic extracted text to the output file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("Extracted Dutch genealogy text\n\n")
                    f.write("Jan van Bulhuis * 1800 Amsterdam † 1870\n")
                    f.write("Maria de Vries ~ 1805 Haarlem\n")
                    f.write("Kinderen:\n")
                    f.write("1. Pieter van Bulhuis * 1825\n")
                return True
            
            mock_processor.process_single_pdf.side_effect = fake_process_pdf
            yield mock_processor

    def test_ocr_service_with_uploaded_files(self, app, db, fake_pdf_file, mock_ocr_processor):
        """
        Test OCRService business logic with real database operations
        
        This test focuses on the service layer and would have caught 
        the missing output_folder attribute because it exercises real 
        TaskManager logic through the complete service workflow.
        """
        pdf_content, pdf_filename = fake_pdf_file
        
        # Create a FileStorage object (what Flask uses for uploaded files)
        pdf_content.seek(0)  # Reset BytesIO position
        uploaded_file = FileStorage(
            stream=pdf_content,
            filename=pdf_filename,
            content_type='application/pdf'
        )
        
        with app.app_context():
            # Test the service directly with real database operations
            service = OCRService(db.session)
            result = service.start_ocr_job([uploaded_file])
            
            # Verify service returned success
            assert result.success is True
            assert result.task_id is not None
            assert 'uploaded files' in result.message
            assert result.files_saved == 1
            
            # Verify file was saved to database
            uploaded_files = JobFile.query.filter_by(job_type='ocr', file_type='input').all()
            assert len(uploaded_files) == 1
            assert uploaded_files[0].filename == pdf_filename
            assert uploaded_files[0].task_id == result.task_id

    def test_ocr_blueprint_http_concerns(self, client, db):
        """
        Test OCR blueprint HTTP handling with mocked service
        
        This tests HTTP concerns: request processing, flash messages, redirects
        while mocking the service layer to isolate HTTP-specific logic.
        """
        fake_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF"
        pdf_content = BytesIO(fake_pdf_content)
        pdf_filename = "test_document.pdf"
        
        # Mock the OCRService to focus on HTTP concerns
        with patch('web_app.blueprints.ocr.OCRService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful service response
            mock_service.start_ocr_job.return_value = JobResult(
                success=True,
                task_id='test-task-id',
                message='OCR job started with 1 uploaded files. Task ID: test-task-id',
                files_saved=1
            )
            
            # Submit request through real HTTP endpoint
            response = client.post('/ocr/start', data={
                'pdf_files': [(pdf_content, pdf_filename)]
            }, content_type='multipart/form-data')
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Verify service was called correctly
            mock_service.start_ocr_job.assert_called_once()
            files_arg = mock_service.start_ocr_job.call_args[0][0]
            assert len(files_arg) == 1
            assert files_arg[0].filename == pdf_filename

    def test_ocr_service_default_folder_handling(self, app, db, mock_ocr_processor):
        """Test OCRService handles empty file list gracefully (service layer)"""
        
        with app.app_context():
            # Test service directly with no files (empty list)
            service = OCRService(db.session)
            result = service.start_ocr_job([])
            
            # Should handle gracefully and use default folder
            assert result.success is True
            assert result.task_id is not None
            assert 'default folder' in result.message
            assert result.files_saved == 0

    def test_ocr_blueprint_no_files_http_handling(self, client, db):
        """Test OCR blueprint HTTP handling with no files (blueprint layer)"""
        
        # Mock the service layer
        with patch('web_app.blueprints.ocr.OCRService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful default folder response
            mock_service.start_ocr_job.return_value = JobResult(
                success=True,
                task_id='test-default-id',
                message='OCR job started using default folder. Task ID: test-default-id',
                files_saved=0
            )
            
            # Submit request with no files
            response = client.post('/ocr/start', data={})
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Verify service was called with empty file list
            mock_service.start_ocr_job.assert_called_once()
            files_arg = mock_service.start_ocr_job.call_args[0][0]
            assert len(files_arg) == 0  # Empty list for no files

    def test_ocr_task_manager_real_path_validation(self):
        """
        Test TaskManager path validation with real directories
        
        This is the specific test that would have caught the output_folder bug.
        Uses real file system operations to verify everything works.
        """
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_manager = OCRTaskManager('test-task', tmp_dir)
            
            # This would fail with AttributeError if output_folder missing
            # Real path validation with real directory creation
            task_manager._validate_paths()
            
            # Verify output_folder exists and is correct
            assert hasattr(task_manager, 'output_folder')
            assert task_manager.output_folder == Path(tmp_dir) / "extracted_text"
            assert task_manager.output_folder.exists()  # Should be created by _validate_paths
            assert task_manager.output_folder.is_dir()

    def test_ocr_error_handling_nonexistent_folder(self):
        """Test OCR error handling when PDF folder doesn't exist - real error"""
        
        nonexistent_path = "/definitely/does/not/exist/folder"
        task_manager = OCRTaskManager('test-task', nonexistent_path)
        
        # Should raise FileNotFoundError for real missing directory
        with pytest.raises(FileNotFoundError, match="PDF folder not found"):
            task_manager._validate_paths()

    def test_ocr_task_manager_file_consolidation(self, app, db):
        """Test TaskManager consolidated file creation with real operations"""
        
        with app.app_context():
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create TaskManager with real temp directory
                task_manager = OCRTaskManager('test-task', tmp_dir)
                task_manager._validate_paths()
                
                # Create some fake extracted text files
                text1_path = task_manager.output_folder / "doc1.txt"
                text2_path = task_manager.output_folder / "doc2.txt"
                
                with open(text1_path, 'w', encoding='utf-8') as f:
                    f.write("Document 1 content\nJan van Bulhuis * 1800")
                    
                with open(text2_path, 'w', encoding='utf-8') as f:
                    f.write("Document 2 content\nMaria de Vries ~ 1805")
                
                # Call real consolidation method
                processed_files = [
                    {'output_file': str(text1_path)},
                    {'output_file': str(text2_path)}
                ]
                
                # This calls real file operations and database storage
                result_id = task_manager._create_consolidated_text_file(processed_files)
                
                # Verify result was stored in database
                assert result_id is not None
                
                result_file = JobFile.query.get(result_id)
                assert result_file is not None
                assert result_file.filename == 'consolidated_text.txt'
                
                # Verify consolidated content includes both files
                content = result_file.file_data.decode('utf-8')
                assert 'doc1.txt' in content
                assert 'doc2.txt' in content  
                assert 'Jan van Bulhuis' in content
                assert 'Maria de Vries' in content


class TestOCRTaskManagerReal:
    """Test OCRTaskManager without any internal mocking"""
    
    def test_task_manager_initialization(self):
        """Test TaskManager initializes correctly with required attributes"""
        
        task_manager = OCRTaskManager('test-task')
        
        # All required attributes should be present (this caught the bug!)
        assert hasattr(task_manager, 'task_id')
        assert hasattr(task_manager, 'pdf_folder')
        assert hasattr(task_manager, 'output_folder')  # This was missing before!
        assert hasattr(task_manager, 'processor')
        assert hasattr(task_manager, 'pdf_files')
        
        # Attributes should have correct values
        assert task_manager.task_id == 'test-task'
        assert isinstance(task_manager.pdf_folder, Path)
        assert isinstance(task_manager.output_folder, Path)
        assert task_manager.output_folder == task_manager.pdf_folder / "extracted_text"
        
    def test_custom_path_initialization(self):
        """Test TaskManager with custom path"""
        
        custom_path = "/custom/pdf/path"
        task_manager = OCRTaskManager('test-task', custom_path)
        
        assert task_manager.pdf_folder_path == custom_path
        assert task_manager.pdf_folder == Path(custom_path)
        assert task_manager.output_folder == Path(custom_path) / "extracted_text"