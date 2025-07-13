"""
Tests for shared service classes
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from web_app.services.extraction_service import ExtractionService, ExtractionTask
from web_app.services.ocr_service import OCRService
from web_app.services.gedcom_service import GedcomService
from web_app.services.research_service import ResearchService
from web_app.services.benchmark_service import BenchmarkService

class TestExtractionService:
    """Test the extraction service"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = ExtractionService()
        assert hasattr(service, 'tasks')
        assert len(service.tasks) == 0
    
    def test_start_extraction_returns_task_id(self):
        """Test that starting extraction returns a task ID"""
        service = ExtractionService()
        
        with patch('web_app.services.extraction_service.LLMGenealogyExtractor'):
            task_id = service.start_extraction()
            assert task_id is not None
            assert task_id in service.tasks
    
    def test_get_task_status(self):
        """Test getting task status"""
        service = ExtractionService()
        
        with patch('web_app.services.extraction_service.LLMGenealogyExtractor'):
            task_id = service.start_extraction()
            status = service.get_task_status(task_id)
            
            assert status is not None
            assert 'id' in status
            assert 'status' in status
            assert status['id'] == task_id

class TestOCRService:
    """Test the OCR service"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = OCRService()
        assert hasattr(service, 'logger')
    
    @patch('web_app.services.ocr_service.PDFOCRProcessor')
    def test_process_pdfs_success(self, mock_processor_class):
        """Test successful PDF processing"""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_all_pdfs.return_value = {"processed": 5}
        
        service = OCRService()
        result = service.process_pdfs()
        
        assert result['success'] is True
        assert 'results' in result
        mock_processor.process_all_pdfs.assert_called_once()
    
    @patch('web_app.services.ocr_service.PDFOCRProcessor')
    def test_process_pdfs_failure(self, mock_processor_class):
        """Test PDF processing failure"""
        mock_processor_class.side_effect = Exception("OCR failed")
        
        service = OCRService()
        result = service.process_pdfs()
        
        assert result['success'] is False
        assert 'error' in result

class TestGedcomService:
    """Test the GEDCOM service"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = GedcomService()
        assert hasattr(service, 'logger')
    
    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_success(self, mock_generator_class):
        """Test successful GEDCOM generation"""
        mock_generator = mock_generator_class.return_value
        mock_generator.generate.return_value = {"families": 5, "people": 20}
        
        service = GedcomService()
        result = service.generate_gedcom()
        
        assert result['success'] is True
        assert 'output_file' in result
        mock_generator.generate.assert_called_once()
    
    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_failure(self, mock_generator_class):
        """Test GEDCOM generation failure"""
        mock_generator_class.side_effect = Exception("GEDCOM failed")
        
        service = GedcomService()
        result = service.generate_gedcom()
        
        assert result['success'] is False
        assert 'error' in result

class TestResearchService:
    """Test the research service"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = ResearchService()
        assert hasattr(service, 'logger')
    
    @patch('web_app.services.research_service.ResearchQuestionGenerator')
    def test_generate_questions_success(self, mock_generator_class):
        """Test successful research question generation"""
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_questions.return_value = [
            "Question 1", "Question 2", "Question 3"
        ]
        
        service = ResearchService()
        result = service.generate_questions()
        
        assert result['success'] is True
        assert 'questions' in result
        assert result['total_questions'] == 3
        mock_generator.generate_questions.assert_called_once()
    
    @patch('web_app.services.research_service.ResearchQuestionGenerator')
    def test_generate_questions_failure(self, mock_generator_class):
        """Test research question generation failure"""
        mock_generator_class.side_effect = Exception("Research failed")
        
        service = ResearchService()
        result = service.generate_questions()
        
        assert result['success'] is False
        assert 'error' in result

class TestBenchmarkService:
    """Test the benchmark service"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = BenchmarkService()
        assert hasattr(service, 'logger')
    
    @patch('web_app.services.benchmark_service.GenealogyModelBenchmark')
    def test_run_benchmark_success(self, mock_benchmark_class):
        """Test successful benchmark run"""
        mock_benchmark = mock_benchmark_class.return_value
        mock_benchmark.run_all_benchmarks.return_value = {
            "models_tested": 3,
            "best_model": "qwen2.5:7b"
        }
        
        service = BenchmarkService()
        result = service.run_benchmark()
        
        assert result['success'] is True
        assert 'results' in result
        mock_benchmark.run_all_benchmarks.assert_called_once()
    
    @patch('web_app.services.benchmark_service.GenealogyModelBenchmark')
    def test_run_benchmark_failure(self, mock_benchmark_class):
        """Test benchmark failure"""
        mock_benchmark_class.side_effect = Exception("Benchmark failed")
        
        service = BenchmarkService()
        result = service.run_benchmark()
        
        assert result['success'] is False
        assert 'error' in result

class TestExtractionTask:
    """Test the extraction task class"""
    
    def test_task_initialization(self):
        """Test task initializes correctly"""
        with patch('web_app.services.extraction_service.LLMGenealogyExtractor'):
            task = ExtractionTask("test-id", Mock())
            
            assert task.id == "test-id"
            assert task.status == 'pending'
            assert task.progress == 0
    
    def test_task_to_dict(self):
        """Test task serialization to dictionary"""
        with patch('web_app.services.extraction_service.LLMGenealogyExtractor'):
            task = ExtractionTask("test-id", Mock())
            task.status = 'running'
            task.progress = 50
            
            data = task.to_dict()
            
            assert data['id'] == "test-id"
            assert data['status'] == 'running'
            assert data['progress'] == 50