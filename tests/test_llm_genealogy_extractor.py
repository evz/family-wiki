"""
Tests for LLM genealogy extractor
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from web_app.pdf_processing.llm_genealogy_extractor import LLMGenealogyExtractor


class TestLLMGenealogyExtractor:
    """Test LLM genealogy extractor functionality"""

    def test_initialization_default(self, app):
        """Test default initialization"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()

            assert extractor.text_file == Path("extracted_text/consolidated_text.txt")
            assert extractor.ollama_host == "192.168.1.234"
            assert extractor.ollama_port == 11434
            assert extractor.ollama_model == "aya:35b-23"
            assert extractor.ollama_base_url == "http://192.168.1.234:11434"
            assert extractor.results == []

    def test_initialization_custom_params(self, app):
        """Test initialization with custom parameters"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
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
    def test_check_ollama_available(self, mock_get, app):
        """Test Ollama availability check when service is running"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': [{'name': 'llama3'}, {'name': 'aya:35b-23'}]}
        mock_get.return_value = mock_response

        extractor = LLMGenealogyExtractor()
        result = extractor.check_ollama()
        assert result is True
        mock_get.assert_called_with("http://192.168.1.234:11434/api/tags", timeout=5)

    @patch('requests.get')
    def test_check_ollama_unavailable(self, mock_get, app):
        """Test Ollama availability check when service is not running"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        extractor = LLMGenealogyExtractor()
        result = extractor.check_ollama()
        assert result is False

    @patch('requests.get')
    def test_check_ollama_error_status(self, mock_get, app):
        """Test Ollama availability check with error status"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        extractor = LLMGenealogyExtractor()
        result = extractor.check_ollama()
        assert result is False

    @patch('requests.post')
    def test_query_ollama_success(self, mock_post, app):
        """Test successful Ollama query"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Generated genealogy data'}
        mock_post.return_value = mock_response

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.query_ollama("Test prompt")
        assert result == 'Generated genealogy data'

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
    def test_query_ollama_with_custom_model(self, mock_post, app):
        """Test Ollama query with custom model"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Custom model response'}
        mock_post.return_value = mock_response

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.query_ollama("Test prompt", model="llama3:8b")
        assert result == 'Custom model response'

        # Check that the custom model was used
        call_args = mock_post.call_args
        assert call_args[1]['json']['model'] == "llama3:8b"

    @patch('requests.post')
    def test_query_ollama_failure(self, mock_post, app):
        """Test Ollama query with request failure"""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.query_ollama("Test prompt")
        assert result is None

    @patch('requests.post')
    def test_query_ollama_error_status(self, mock_post, app):
        """Test Ollama query with error HTTP status"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.query_ollama("Test prompt")
        assert result is None

    def test_create_genealogy_prompt(self, app):
        """Test genealogy prompt creation"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()

        text_chunk = "Jan van der Berg * 1850 Amsterdam"
        prompt = extractor.create_genealogy_prompt(text_chunk)

        assert "Dutch genealogist" in prompt
        assert text_chunk in prompt
        assert "families" in prompt
        assert "JSON" in prompt

    def test_split_text_intelligently_basic(self, app):
        """Test basic text splitting functionality"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()

        # Use Dutch genealogy format that the method expects
        text = """
        EERSTE GENERATIE

        1.1 Kinderen van Jan van der Berg:
        Jan van der Berg * 1850 Amsterdam + 1920 Amsterdam
        Hij trouwde met Maria Jansen * 1855 Utrecht + 1925 Amsterdam

        Kinderen:
        a. Piet van der Berg * 1875 Amsterdam
        b. Marie van der Berg * 1877 Amsterdam
        c. Hendrik van der Berg * 1880 Amsterdam
        """
        chunks = extractor.split_text_intelligently(text)

        assert len(chunks) >= 1
        # All chunks should be strings
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_split_text_intelligently_with_families(self, app):
        """Test text splitting with multiple generations"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()

        text = """
        EERSTE GENERATIE

        1.1 Kinderen van Jan van der Berg:
        Jan van der Berg * 1850 Amsterdam + 1920 Amsterdam trouwde met Maria Jansen
        Kinderen: a. Piet van der Berg * 1875, b. Marie van der Berg * 1877

        TWEEDE GENERATIE

        2.1 Kinderen van Hendrik Jansen:
        Hendrik Jansen * 1860 Rotterdam + 1930 Rotterdam trouwde met Anna de Vries
        Kinderen: a. Willem Jansen * 1885, b. Sara Jansen * 1887, c. Dirk Jansen * 1890
        """
        chunks = extractor.split_text_intelligently(text)

        # Should return chunks for multiple generations
        assert len(chunks) >= 1
        # All chunks should be strings
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_split_text_intelligently_empty(self, app):
        """Test text splitting with empty text"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=False):
            extractor = LLMGenealogyExtractor()

        chunks = extractor.split_text_intelligently("")
        assert chunks == []

    @patch.object(LLMGenealogyExtractor, 'query_ollama')
    def test_extract_from_chunk_valid_json(self, mock_query, app):
        """Test extraction from chunk with valid JSON response"""
        valid_json = {
            "families": [
                {
                    "family_id": "1",
                    "parents": {
                        "father": {
                            "given_names": "Jan",
                            "surname": "van der Berg"
                        }
                    },
                    "children": []
                }
            ],
            "isolated_individuals": []
        }
        mock_query.return_value = json.dumps(valid_json)

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.extract_from_chunk("Test text", custom_prompt="Test prompt")
        assert result == valid_json

    @patch.object(LLMGenealogyExtractor, 'query_ollama')
    def test_extract_from_chunk_invalid_json(self, mock_query, app):
        """Test extraction from chunk with invalid JSON response"""
        mock_query.return_value = "This is not valid JSON"

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.extract_from_chunk("Test text", custom_prompt="Test prompt")
        assert result == {"families": [], "isolated_individuals": []}

    @patch.object(LLMGenealogyExtractor, 'query_ollama')
    def test_extract_from_chunk_no_response(self, mock_query, app):
        """Test extraction from chunk with no LLM response"""
        mock_query.return_value = None

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.extract_from_chunk("Test text", custom_prompt="Test prompt")
        assert result == {"families": [], "isolated_individuals": []}

    @patch.object(LLMGenealogyExtractor, 'query_ollama')
    def test_extract_from_chunk_with_custom_prompt(self, mock_query, app):
        """Test extraction with custom prompt"""
        mock_query.return_value = '{"families": []}'

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        custom_prompt = "Custom extraction prompt"
        extractor.extract_from_chunk("Test text", custom_prompt=custom_prompt)

        # Verify custom prompt was used
        mock_query.assert_called_once_with(custom_prompt)

    @patch.object(LLMGenealogyExtractor, 'query_ollama')
    def test_extract_from_chunk_json_with_extra_text(self, mock_query, app):
        """Test extraction with JSON surrounded by extra text"""
        json_with_text = """
        Here is the extracted data:
        {"families": [{"family_id": "test"}]}
        Additional notes about the extraction.
        """
        mock_query.return_value = json_with_text

        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor()

        result = extractor.extract_from_chunk("Test text", custom_prompt="Test prompt")
        assert result == {"families": [{"family_id": "test"}], "isolated_individuals": []}


    @patch.object(LLMGenealogyExtractor, 'split_text_intelligently')
    @patch.object(LLMGenealogyExtractor, 'extract_from_chunk')
    def test_process_all_text_file_not_found(self, mock_extract, mock_split, app):
        """Test processing when text file doesn't exist"""
        with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
            extractor = LLMGenealogyExtractor(text_file="nonexistent.txt")

        result = extractor.process_all_text()
        assert result is None  # Method returns None
        mock_split.assert_not_called()
        mock_extract.assert_not_called()

    @patch.object(LLMGenealogyExtractor, 'extract_from_chunk')
    def test_process_all_text_success(self, mock_extract, app):
        """Test successful text processing"""
        # Create temporary text file with Dutch genealogy content that will be processed
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("""
            EERSTE GENERATIE

            1.1 Kinderen van Jan van der Berg:
            Jan van der Berg * 1850 Amsterdam + 1920 Amsterdam trouwde met Maria Jansen
            Kinderen: a. Piet van der Berg * 1875, b. Marie van der Berg * 1877
            """)
            temp_path = temp_file.name

        try:
            with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
                extractor = LLMGenealogyExtractor(text_file=temp_path)

            mock_extract.return_value = {"families": [{"family_id": "test"}], "isolated_individuals": []}

            result = extractor.process_all_text()
            assert result is None  # Method returns None
            mock_extract.assert_called()
        finally:
            Path(temp_path).unlink()

    @patch.object(LLMGenealogyExtractor, 'extract_from_chunk')
    def test_process_all_text_ollama_failure(self, mock_extract, app):
        """Test processing with Ollama extraction failures"""
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("Test family data here")
            temp_path = temp_file.name

        try:
            with patch.object(LLMGenealogyExtractor, 'check_ollama', return_value=True):
                extractor = LLMGenealogyExtractor(text_file=temp_path)

            mock_extract.return_value = None  # Simulate extraction failure

            result = extractor.process_all_text()
            assert result is None  # Method returns None
        finally:
            Path(temp_path).unlink()

