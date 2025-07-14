"""
Tests for LLM genealogy extractor
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from web_app.pdf_processing.llm_genealogy_extractor import LLMGenealogyExtractor


class TestLLMGenealogyExtractor:
    """Test LLM genealogy extractor functionality"""

    def test_initialization_default(self):
        """Test default initialization"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
            assert extractor.text_file == Path("extracted_text/consolidated_text.txt")
            assert extractor.ollama_host == "192.168.1.234"
            assert extractor.ollama_port == 11434
            assert extractor.ollama_model == "aya:35b-23"
            assert extractor.ollama_base_url == "http://192.168.1.234:11434"
            assert extractor.results == []

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor(
                text_file="custom_text.txt",
                ollama_host="localhost",
                ollama_port=8080,
                ollama_model="llama3:8b"
            )
            
            assert extractor.text_file == Path("custom_text.txt")
            assert extractor.ollama_host == "localhost"
            assert extractor.ollama_port == 8080
            assert extractor.ollama_model == "llama3:8b"
            assert extractor.ollama_base_url == "http://localhost:8080"

    @patch('requests.get')
    def test_check_ollama_available(self, mock_get):
        """Test Ollama availability check when service is running"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': [{'name': 'llama3'}, {'name': 'aya:35b-23'}]}
        mock_get.return_value = mock_response
        
        with patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.check_ollama()
        assert result is True
        mock_get.assert_called_with("http://192.168.1.234:11434/api/tags", timeout=5)

    @patch('requests.get')
    def test_check_ollama_unavailable(self, mock_get):
        """Test Ollama availability check when service is not running"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.check_ollama()
        assert result is False
        mock_get.assert_called_with("http://192.168.1.234:11434/api/tags", timeout=5)

    @patch('requests.get')
    def test_check_ollama_error_status(self, mock_get):
        """Test Ollama availability check with error status"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        with patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.check_ollama()
        assert result is False

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_check_openai_available(self):
        """Test OpenAI availability check when API key is set"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.check_openai()
        assert result is True

    @patch.dict('os.environ', {}, clear=True)
    def test_check_openai_unavailable(self):
        """Test OpenAI availability check when API key is not set"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.check_openai()
        assert result is False

    @patch('requests.post')
    def test_query_ollama_success(self, mock_post):
        """Test successful Ollama query"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test response from Ollama'}
        mock_post.return_value = mock_response
        
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.query_ollama("Test prompt")
        assert result == "Test response from Ollama"
        
        mock_post.assert_called_once_with(
            "http://192.168.1.234:11434/api/generate",
            json={
                "model": "aya:35b-23",
                "prompt": "Test prompt",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            },
            timeout=120
        )

    @patch('requests.post')
    def test_query_ollama_with_custom_model(self, mock_post):
        """Test Ollama query with custom model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test response'}
        mock_post.return_value = mock_response
        
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.query_ollama("Test prompt", model="llama3:8b")
        assert result == "Test response"
        
        # Check that custom model was used
        call_args = mock_post.call_args
        assert call_args[1]['json']['model'] == "llama3:8b"

    @patch('requests.post')
    def test_query_ollama_failure(self, mock_post):
        """Test Ollama query failure"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.query_ollama("Test prompt")
        assert result is None

    @patch('requests.post')
    def test_query_ollama_error_status(self, mock_post):
        """Test Ollama query with error status"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        result = extractor.query_ollama("Test prompt")
        assert result is None

    def test_create_genealogy_prompt(self):
        """Test genealogy prompt creation"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        text_chunk = "Jan Jansen * 1800 Amsterdam"
        prompt = extractor.create_genealogy_prompt(text_chunk)
        
        assert "You are an expert Dutch genealogist" in prompt
        assert "Jan Jansen * 1800 Amsterdam" in prompt
        assert "* means birth, ~ means baptism, + means death, x means marriage" in prompt
        assert "Kinderen van" in prompt
        assert "families" in prompt
        assert "isolated_individuals" in prompt

    def test_split_text_intelligently_basic(self):
        """Test basic text splitting"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        # Use realistic text that will produce chunks
        text = "EERSTE GENERATIE\n\nJan Jansen * 1800 Amsterdam. Hij was een bekende koopman in de stad en had veel contacten met andere families. Hij trouwde met Maria Pieterse en samen kregen zij verschillende kinderen die allemaal een belangrijke rol speelden in de geschiedenis van de familie.\n\nTWEEDE GENERATIE\n\nPieter Jansen * 1825 Amsterdam. Zoon van Jan Jansen en Maria Pieterse. Hij volgde zijn vader op als koopman."
        chunks = extractor.split_text_intelligently(text)
        
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) <= 4000  # Max chunk size

    def test_split_text_intelligently_with_families(self):
        """Test text splitting with family groups"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        # Use realistic family text that will produce chunks
        text = "1.1. Kinderen van Jan Jansen en Maria Pieterse:\na. Pieter Jansen * 1825 Amsterdam, getrouwd met Anna de Vries\nb. Maria Jansen * 1827 Amsterdam, getrouwd met Willem van der Berg\nc. Johannes Jansen * 1829 Amsterdam, ongehuwd gestorven\n\nDeze familie was zeer prominent in de Amsterdamse samenleving en had uitgebreide handelscontacten."
        chunks = extractor.split_text_intelligently(text)
        
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_split_text_intelligently_empty(self):
        """Test text splitting with empty text"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        chunks = extractor.split_text_intelligently("")
        assert len(chunks) == 0

    def test_extract_from_chunk_valid_json(self):
        """Test extracting from chunk with valid JSON response"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        response = '''
        {
          "families": [
            {
              "family_id": "1.1",
              "parents": {
                "father": {
                  "given_names": "Jan",
                  "surname": "Jansen",
                  "birth_date": "1800",
                  "confidence": 0.9
                }
              },
              "children": [
                {
                  "given_names": "Pieter",
                  "surname": "Jansen",
                  "birth_date": "1825",
                  "confidence": 0.8
                }
              ]
            }
          ],
          "isolated_individuals": []
        }
        '''
        
        with patch.object(extractor, 'query_ollama', return_value=response):
            result = extractor.extract_from_chunk("Test chunk")
            
        assert result is not None
        assert 'families' in result
        assert 'isolated_individuals' in result
        assert len(result['families']) == 1
        assert result['families'][0]['family_id'] == "1.1"

    def test_extract_from_chunk_invalid_json(self):
        """Test extracting from chunk with invalid JSON response"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        response = "This is not valid JSON"
        with patch.object(extractor, 'query_ollama', return_value=response):
            result = extractor.extract_from_chunk("Test chunk")
            
        assert result is not None
        assert result == {"families": [], "isolated_individuals": []}

    def test_extract_from_chunk_no_response(self):
        """Test extracting from chunk when LLM returns no response"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        with patch.object(extractor, 'query_ollama', return_value=None):
            result = extractor.extract_from_chunk("Test chunk")
            
        assert result is not None
        assert result == {"families": [], "isolated_individuals": []}

    def test_extract_from_chunk_with_custom_prompt(self):
        """Test extracting from chunk with custom prompt"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        custom_prompt = "Custom prompt: {text_chunk}"
        response = '{"families": [], "isolated_individuals": []}'
        
        with patch.object(extractor, 'query_ollama', return_value=response) as mock_query:
            result = extractor.extract_from_chunk("Test chunk", custom_prompt=custom_prompt)
            
        assert result is not None
        # Check that custom prompt was used
        mock_query.assert_called_once_with("Custom prompt: Test chunk")

    def test_extract_from_chunk_json_with_extra_text(self):
        """Test extracting from chunk with JSON buried in extra text"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        response = '''
        Here is my analysis:
        
        {"families": [], "isolated_individuals": []}
        
        This completes the extraction.
        '''
        
        with patch.object(extractor, 'query_ollama', return_value=response):
            result = extractor.extract_from_chunk("Test chunk")
            
        assert result is not None
        assert 'families' in result
        assert 'isolated_individuals' in result

    def test_save_results(self):
        """Test saving results to file"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        # Results should be a dictionary after processing
        test_results = {
            "families": [{"family_id": "1.1", "parents": {}, "children": []}], 
            "isolated_individuals": [{"given_names": "Jan", "surname": "Jansen"}]
        }
        extractor.results = test_results
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name
        
        try:
            extractor.save_results(output_file)
            
            # Verify file was created and contains correct data structure
            with open(output_file, 'r') as f:
                saved_data = json.load(f)
                
            assert 'metadata' in saved_data
            assert 'families' in saved_data
            assert 'isolated_individuals' in saved_data
            assert saved_data['families'] == test_results['families']
            assert saved_data['isolated_individuals'] == test_results['isolated_individuals']
        finally:
            Path(output_file).unlink()

    def test_save_results_empty(self):
        """Test saving empty results to file"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        # Results start as empty list but save_results expects dictionary structure
        extractor.results = {"families": [], "isolated_individuals": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name
        
        try:
            extractor.save_results(output_file)
            
            # Verify file was created and contains empty results with proper structure
            with open(output_file, 'r') as f:
                saved_data = json.load(f)
                
            assert 'metadata' in saved_data
            assert 'families' in saved_data
            assert 'isolated_individuals' in saved_data
            assert saved_data['families'] == []
            assert saved_data['isolated_individuals'] == []
        finally:
            Path(output_file).unlink()

    def test_process_all_text_file_not_found(self):
        """Test processing when text file doesn't exist"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor(text_file="non_existent_file.txt")
            
        # Should not raise an exception but results should remain as empty list
        extractor.process_all_text()
        assert extractor.results == []

    def test_process_all_text_success(self):
        """Test successful processing of text file"""
        # Create a temporary text file with realistic content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("EERSTE GENERATIE\n\nJan Jansen * 1800 Amsterdam. Hij was een bekende koopman.\n\nTWEEDE GENERATIE\n\nPieter Jansen * 1825 Amsterdam, zoon van Jan Jansen.")
            text_file = f.name
        
        try:
            with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
                 patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
                extractor = LLMGenealogyExtractor(text_file=text_file)
                
            # Mock the Ollama response
            mock_response = '{"families": [], "isolated_individuals": []}'
            with patch.object(extractor, 'query_ollama', return_value=mock_response):
                extractor.process_all_text()
                
            # After processing, results should be a dictionary
            assert isinstance(extractor.results, dict)
            assert 'families' in extractor.results
            assert 'isolated_individuals' in extractor.results
        finally:
            Path(text_file).unlink()

    def test_process_all_text_ollama_failure(self):
        """Test processing when Ollama queries fail"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("EERSTE GENERATIE\n\nJan Jansen * 1800 Amsterdam. Hij was een bekende koopman.")
            text_file = f.name
        
        try:
            with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True), \
                 patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
                extractor = LLMGenealogyExtractor(text_file=text_file)
                
            # Mock Ollama to return None (failure)
            with patch.object(extractor, 'query_ollama', return_value=None):
                extractor.process_all_text()
                
            # Should have results with empty families/individuals due to failed queries
            assert isinstance(extractor.results, dict)
            assert 'families' in extractor.results
            assert 'isolated_individuals' in extractor.results
            assert extractor.results['families'] == []
            assert extractor.results['isolated_individuals'] == []
        finally:
            Path(text_file).unlink()

    def test_print_summary(self):
        """Test printing summary of results"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        # Add some test results in dictionary format
        extractor.results = {
            "families": [{"family_id": "1.1", "parents": {}, "children": []}], 
            "isolated_individuals": [{"given_names": "John", "surname": "Doe"}]
        }
        
        # Should not raise an exception
        extractor.print_summary()
        
    def test_print_summary_empty_results(self):
        """Test printing summary with empty results"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False), \
             patch.object(LLMGenealogyExtractor, 'check_openai', return_value=False):
            extractor = LLMGenealogyExtractor()
            
        # Set empty results in dictionary format
        extractor.results = {"families": [], "isolated_individuals": []}
        
        # Should not raise an exception with empty results
        extractor.print_summary()