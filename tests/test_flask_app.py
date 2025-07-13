"""
Tests for Flask application and CLI commands
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create CLI test runner"""
    return app.test_cli_runner()

class TestFlaskApp:
    """Test Flask application"""
    
    def test_app_creation(self, app):
        """Test app creates successfully"""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_index_route(self, client):
        """Test index route"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Family Wiki' in response.data
    
    def test_status_api(self, client):
        """Test status API endpoint"""
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'running'
        assert 'tools' in data
    
    def test_tool_page(self, client):
        """Test tool detail pages"""
        response = client.get('/tools/ocr')
        assert response.status_code == 200
        assert b'OCR Processing' in response.data
    
    def test_invalid_tool_page(self, client):
        """Test invalid tool page redirects"""
        response = client.get('/tools/invalid')
        assert response.status_code == 302  # Redirect to index
    
    @patch('web_app.services.ocr_service.ocr_service.process_pdfs')
    def test_run_ocr_api(self, mock_process, client):
        """Test OCR API endpoint"""
        mock_process.return_value = {'success': True, 'message': 'OCR completed'}
        
        response = client.get('/api/run/ocr')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        mock_process.assert_called_once()
    
    def test_run_invalid_tool_api(self, client):
        """Test invalid tool API returns error"""
        response = client.get('/api/run/invalid')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

class TestCLICommands:
    """Test Flask CLI commands"""
    
    @patch('web_app.services.ocr_service.ocr_service.process_pdfs')
    def test_ocr_command(self, mock_process, runner):
        """Test OCR CLI command"""
        mock_process.return_value = {'success': True, 'results': {}}
        
        result = runner.invoke(args=['ocr'])
        assert result.exit_code == 0
        assert 'OCR processing completed' in result.output
        mock_process.assert_called_once()
    
    @patch('web_app.services.ocr_service.ocr_service.process_pdfs')
    def test_ocr_command_failure(self, mock_process, runner):
        """Test OCR CLI command failure"""
        mock_process.return_value = {'success': False, 'error': 'OCR failed'}
        
        result = runner.invoke(args=['ocr'])
        assert result.exit_code == 1
        assert 'OCR processing failed' in result.output
    
    @patch('web_app.services.gedcom_service.gedcom_service.generate_gedcom')
    def test_gedcom_command(self, mock_generate, runner):
        """Test GEDCOM CLI command"""
        mock_generate.return_value = {
            'success': True, 
            'output_file': 'test.ged',
            'results': {}
        }
        
        result = runner.invoke(args=['gedcom'])
        assert result.exit_code == 0
        assert 'GEDCOM generation completed' in result.output
        mock_generate.assert_called_once()
    
    @patch('web_app.services.research_service.research_service.generate_questions')
    def test_research_command(self, mock_generate, runner):
        """Test research CLI command"""
        mock_generate.return_value = {
            'success': True,
            'questions': ['Question 1', 'Question 2'],
            'total_questions': 2
        }
        
        result = runner.invoke(args=['research'])
        assert result.exit_code == 0
        assert 'Research questions generated' in result.output
        mock_generate.assert_called_once()
    
    @patch('web_app.services.benchmark_service.benchmark_service.run_benchmark')
    def test_benchmark_command(self, mock_benchmark, runner):
        """Test benchmark CLI command"""
        mock_benchmark.return_value = {'success': True, 'results': {}}
        
        result = runner.invoke(args=['benchmark'])
        assert result.exit_code == 0
        assert 'Model benchmark completed' in result.output
        mock_benchmark.assert_called_once()
    
    def test_status_command(self, runner):
        """Test status CLI command"""
        result = runner.invoke(args=['status'])
        assert result.exit_code == 0
        assert 'Family Wiki Tools Status' in result.output
        assert 'Available Commands' in result.output
    
    @patch('web_app.services.extraction_service.extraction_service.start_extraction')
    @patch('web_app.services.extraction_service.extraction_service.get_task_status')
    def test_extract_command(self, mock_status, mock_start, runner):
        """Test extract CLI command"""
        mock_start.return_value = 'test-task-id'
        mock_status.return_value = {
            'status': 'completed',
            'summary': {'total_families': 5, 'total_people': 20}
        }
        
        result = runner.invoke(args=['extract'])
        assert result.exit_code == 0
        assert 'Extraction completed' in result.output
        mock_start.assert_called_once()
    
    def test_verbose_flag(self, runner):
        """Test verbose flag works with commands"""
        with patch('web_app.services.ocr_service.ocr_service.process_pdfs') as mock_process:
            mock_process.return_value = {'success': True, 'results': {}}
            
            result = runner.invoke(args=['ocr', '--verbose'])
            assert result.exit_code == 0
            # Verbose flag should be passed to callback
            mock_process.assert_called_once()