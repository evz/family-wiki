"""
Integration tests for file job blueprints - Two-Layer Integration Testing Pattern

Layer 2: Blueprint HTTP Tests - Test HTTP concerns with mocked services

Tests the file job blueprints (OCR, Extraction, Research, GEDCOM) using 
pytest parametrization to reduce duplication while testing flash messages
and error handling scenarios.
"""
import pytest
from unittest.mock import Mock, patch
from flask import url_for
from io import BytesIO

from web_app.services.file_job_service import JobResult


class TestFileJobBlueprintsHTTP:
    """Test file job blueprints HTTP concerns with mocked services"""

    @pytest.mark.parametrize("blueprint_info", [
        {
            'endpoint': '/ocr/start',
            'service_path': 'web_app.blueprints.ocr.OCRService',
            'service_method': 'start_ocr_job',
            'file_param': 'pdf_files',
            'test_files': [('test1.pdf', b'pdf content 1'), ('test2.pdf', b'pdf content 2')],
            'job_type': 'OCR',
            'default_message': 'OCR job started using default folder. Task ID: ocr-task-123'
        },
        {
            'endpoint': '/extraction/start', 
            'service_path': 'web_app.blueprints.extraction.ExtractionService',
            'service_method': 'start_extraction_job',
            'file_param': 'text_file',
            'test_files': [('extracted.txt', b'extracted text content')],
            'job_type': 'Extraction',
            'default_message': 'Extraction job started using latest OCR results. Task ID: extraction-task-123'
        },
        {
            'endpoint': '/research/start',
            'service_path': 'web_app.blueprints.research.ResearchService', 
            'service_method': 'start_research_job',
            'file_param': 'input_file',
            'test_files': [('genealogy.json', b'genealogy data for research')],
            'job_type': 'Research',
            'default_message': 'Research questions job started using latest extraction results. Task ID: research-task-123'
        },
        {
            'endpoint': '/gedcom/start',
            'service_path': 'web_app.blueprints.gedcom.GedcomJobService',
            'service_method': 'start_gedcom_job', 
            'file_param': 'input_file',
            'test_files': [('extraction.json', b'extraction results for gedcom')],
            'job_type': 'GEDCOM',
            'default_message': 'GEDCOM generation job started using latest extraction results. Task ID: gedcom-task-123'
        }
    ])
    def test_blueprint_no_files_success(self, client, db, blueprint_info):
        """Test blueprint with no files - should use default behavior and flash success message"""
        
        with patch(blueprint_info['service_path']) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful service response
            getattr(mock_service, blueprint_info['service_method']).return_value = JobResult(
                success=True,
                task_id=f"{blueprint_info['job_type'].lower()}-task-123",
                message=blueprint_info['default_message']
            )
            
            # Submit form with no files
            with client.session_transaction() as sess:
                # Clear any existing flashes
                sess.pop('_flashes', None)
            
            response = client.post(blueprint_info['endpoint'])
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Verify service was called with empty file list
            getattr(mock_service, blueprint_info['service_method']).assert_called_once_with([])
            
            # Verify success flash message
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
                assert len(flashes) == 1
                category, message = flashes[0]
                assert category == 'success'
                assert blueprint_info['default_message'] in message

    @pytest.mark.parametrize("blueprint_info", [
        {
            'endpoint': '/ocr/start',
            'service_path': 'web_app.blueprints.ocr.OCRService',
            'service_method': 'start_ocr_job',
            'file_param': 'pdf_files',
            'test_files': [('test1.pdf', b'pdf content 1'), ('test2.pdf', b'pdf content 2')],
            'job_type': 'OCR'
        },
        {
            'endpoint': '/extraction/start',
            'service_path': 'web_app.blueprints.extraction.ExtractionService', 
            'service_method': 'start_extraction_job',
            'file_param': 'text_file',
            'test_files': [('extracted.txt', b'extracted text content')],
            'job_type': 'Extraction'
        },
        {
            'endpoint': '/research/start',
            'service_path': 'web_app.blueprints.research.ResearchService',
            'service_method': 'start_research_job', 
            'file_param': 'input_file',
            'test_files': [('genealogy.json', b'genealogy data for research')],
            'job_type': 'Research'
        },
        {
            'endpoint': '/gedcom/start',
            'service_path': 'web_app.blueprints.gedcom.GedcomJobService',
            'service_method': 'start_gedcom_job',
            'file_param': 'input_file', 
            'test_files': [('extraction.json', b'extraction results for gedcom')],
            'job_type': 'GEDCOM'
        }
    ])
    def test_blueprint_with_files_success(self, client, db, blueprint_info):
        """Test blueprint with uploaded files - should flash success message with file count"""
        
        with patch(blueprint_info['service_path']) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful service response
            files_count = len(blueprint_info['test_files'])
            success_message = f"{blueprint_info['job_type']} job started with {files_count} uploaded files. Task ID: {blueprint_info['job_type'].lower()}-task-456"
            getattr(mock_service, blueprint_info['service_method']).return_value = JobResult(
                success=True,
                task_id=f"{blueprint_info['job_type'].lower()}-task-456",
                message=success_message,
                files_saved=files_count
            )
            
            # Create test files
            if blueprint_info['file_param'] == 'pdf_files':
                # OCR accepts multiple files
                files_data = {
                    blueprint_info['file_param']: [
                        (BytesIO(content), filename) 
                        for filename, content in blueprint_info['test_files']
                    ]
                }
            else:
                # Other blueprints accept single file
                filename, content = blueprint_info['test_files'][0]
                files_data = {
                    blueprint_info['file_param']: (BytesIO(content), filename)
                }
            
            # Clear any existing flashes
            with client.session_transaction() as sess:
                sess.pop('_flashes', None)
            
            # Submit form with files
            response = client.post(blueprint_info['endpoint'], data=files_data)
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Verify service was called with file list
            getattr(mock_service, blueprint_info['service_method']).assert_called_once()
            
            # Verify success flash message mentions uploaded files
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
                assert len(flashes) == 1
                category, message = flashes[0]
                assert category == 'success'
                assert 'uploaded files' in message
                assert blueprint_info['job_type'] in message

    @pytest.mark.parametrize("blueprint_info", [
        {
            'endpoint': '/ocr/start',
            'service_path': 'web_app.blueprints.ocr.OCRService',
            'service_method': 'start_ocr_job',
            'job_type': 'OCR',
            'error_message': 'OCR processor temporarily unavailable',
            'flash_job_name': 'OCR'  # What appears in flash messages
        },
        {
            'endpoint': '/extraction/start',
            'service_path': 'web_app.blueprints.extraction.ExtractionService',
            'service_method': 'start_extraction_job', 
            'job_type': 'Extraction',
            'error_message': 'LLM service temporarily unavailable',
            'flash_job_name': 'extraction'  # What appears in flash messages
        },
        {
            'endpoint': '/research/start',
            'service_path': 'web_app.blueprints.research.ResearchService',
            'service_method': 'start_research_job',
            'job_type': 'Research',
            'error_message': 'Research service temporarily unavailable',
            'flash_job_name': 'research'  # What appears in flash messages
        },
        {
            'endpoint': '/gedcom/start',
            'service_path': 'web_app.blueprints.gedcom.GedcomJobService',
            'service_method': 'start_gedcom_job',
            'job_type': 'GEDCOM',
            'error_message': 'GEDCOM service temporarily unavailable',
            'flash_job_name': 'GEDCOM'  # What appears in flash messages
        }
    ])
    def test_blueprint_service_error_handling(self, client, db, blueprint_info):
        """Test blueprint handles service errors correctly - should flash error message and redirect"""
        
        with patch(blueprint_info['service_path']) as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock service error response
            getattr(mock_service, blueprint_info['service_method']).return_value = JobResult(
                success=False,
                error=blueprint_info['error_message']
            )
            
            # Clear any existing flashes
            with client.session_transaction() as sess:
                sess.pop('_flashes', None)
            
            # Submit form
            response = client.post(blueprint_info['endpoint'])
            
            # Verify HTTP response - should redirect (not crash)
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Verify service was called
            getattr(mock_service, blueprint_info['service_method']).assert_called_once()
            
            # Verify error flash message
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
                assert len(flashes) == 1
                category, message = flashes[0]
                assert category == 'error'
                assert f'Failed to start {blueprint_info["flash_job_name"]} job:' in message  # Use exact flash message format
                assert blueprint_info['error_message'] in message

    def test_ocr_blueprint_multiple_files_flash_message(self, client, db):
        """Test OCR blueprint with multiple files shows correct count in flash message"""
        
        with patch('web_app.blueprints.ocr.OCRService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock successful service response
            mock_service.start_ocr_job.return_value = JobResult(
                success=True,
                task_id="ocr-task-789",
                message="OCR job started with 3 uploaded files. Task ID: ocr-task-789",
                files_saved=3
            )
            
            # Create multiple test files
            test_files = [
                (BytesIO(b'pdf1'), 'file1.pdf'),
                (BytesIO(b'pdf2'), 'file2.pdf'),
                (BytesIO(b'pdf3'), 'file3.pdf')
            ]
            
            # Clear any existing flashes
            with client.session_transaction() as sess:
                sess.pop('_flashes', None)
            
            # Submit form with multiple files
            response = client.post('/ocr/start', data={'pdf_files': test_files})
            
            # Verify HTTP response
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Verify service was called with multiple files
            mock_service.start_ocr_job.assert_called_once()
            call_args = mock_service.start_ocr_job.call_args[0][0]
            assert len(call_args) == 3  # Three files passed
            
            # Verify success flash message mentions 3 files
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
                assert len(flashes) == 1
                category, message = flashes[0]
                assert category == 'success'
                assert '3 uploaded files' in message

    @pytest.mark.parametrize("blueprint_info", [
        {
            'endpoint': '/ocr/start',
            'service_path': 'web_app.blueprints.ocr.OCRService',
            'service_method': 'start_ocr_job',
            'job_type': 'OCR'
        },
        {
            'endpoint': '/extraction/start',
            'service_path': 'web_app.blueprints.extraction.ExtractionService',
            'service_method': 'start_extraction_job', 
            'job_type': 'Extraction'
        },
        {
            'endpoint': '/research/start',
            'service_path': 'web_app.blueprints.research.ResearchService',
            'service_method': 'start_research_job',
            'job_type': 'Research'
        },
        {
            'endpoint': '/gedcom/start',
            'service_path': 'web_app.blueprints.gedcom.GedcomJobService',
            'service_method': 'start_gedcom_job',
            'job_type': 'GEDCOM'
        }
    ])
    def test_blueprint_service_exception_handling(self, client, db, blueprint_info):
        """Test blueprint handles service instantiation exceptions gracefully"""
        
        with patch(blueprint_info['service_path']) as mock_service_class:
            # Mock service constructor raising exception
            mock_service_class.side_effect = Exception("Database connection failed")
            
            # Clear any existing flashes
            with client.session_transaction() as sess:
                sess.pop('_flashes', None)
            
            # Submit request - should be handled by @handle_blueprint_errors
            response = client.post(blueprint_info['endpoint'])
            
            # Should redirect to main page (error handler should catch this)
            assert response.status_code == 302
            assert response.location == url_for('main.index')
            
            # Should have an error flash message
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
                assert len(flashes) >= 1  # At least one error message
                # Find the error flash
                error_flashes = [f for f in flashes if f[0] == 'error']
                assert len(error_flashes) >= 1