"""
Tests for GEDCOM service
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from web_app.services.gedcom_service import GedcomService, LLMGEDCOMGenerator


class TestLLMGEDCOMGenerator:
    """Test LLMGEDCOMGenerator class"""

    @pytest.fixture
    def sample_llm_data(self):
        """Sample LLM data for testing"""
        return {
            "people": [
                {
                    "given_names": "Johannes",
                    "surname": "van der Berg",
                    "birth_date": "15 maart 1850",
                    "birth_place": "Amsterdam",
                    "baptism_date": "20 maart 1850",
                    "baptism_place": "Nieuwe Kerk Amsterdam",
                    "death_date": "3 december 1920",
                    "death_place": "Rotterdam",
                    "notes": "Bakker van beroep",
                    "confidence": 0.9
                },
                {
                    "given_names": "Maria Elisabeth",
                    "surname": "de Jong",
                    "birth_date": "2 juli 1855",
                    "birth_place": "Utrecht",
                    "death_date": "",
                    "notes": "",
                    "confidence": 0.8
                }
            ]
        }

    @pytest.fixture
    def temp_json_file(self, sample_llm_data):
        """Create temporary JSON file with sample data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_llm_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        import os
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_generator_initialization(self):
        """Test generator initialization"""
        generator = LLMGEDCOMGenerator("test.json")

        assert generator.llm_data_file == Path("test.json")
        assert generator.gedcom_writer is not None

    def test_load_llm_data_file_not_found(self):
        """Test loading data when file doesn't exist"""
        generator = LLMGEDCOMGenerator("nonexistent.json")

        people = generator.load_llm_data()

        assert people == []

    @patch('web_app.services.gedcom_service.DutchNameParser')
    @patch('web_app.services.gedcom_service.DutchDateParser')
    def test_load_llm_data_success(self, mock_date_parser, mock_name_parser, temp_json_file):
        """Test successful data loading"""
        # Mock parser responses
        mock_name_parser.parse_full_name.side_effect = [
            ("Johannes", "van der", "Berg"),
            ("Maria Elisabeth", "", "de Jong")
        ]
        mock_date_parser.parse_dutch_date.side_effect = [
            "15 MAR 1850",  # birth
            "20 MAR 1850",  # baptism
            "3 DEC 1920",   # death
            "2 JUL 1855",   # birth
            "",             # baptism (empty)
            ""              # death (empty)
        ]

        generator = LLMGEDCOMGenerator(temp_json_file)
        people = generator.load_llm_data()

        assert len(people) == 2

        # Check first person
        person1 = people[0]
        assert person1.id == "I0001"
        assert person1.given_names == "Johannes"
        assert person1.tussenvoegsel == "van der"
        assert person1.surname == "Berg"
        assert person1.birth_date == "15 MAR 1850"
        assert person1.birth_place == "Amsterdam"
        assert person1.baptism_date == "20 MAR 1850"
        assert person1.baptism_place == "Nieuwe Kerk Amsterdam"
        assert person1.death_date == "3 DEC 1920"
        assert person1.death_place == "Rotterdam"
        assert person1.notes == "Bakker van beroep"
        assert person1.confidence_score == 0.9

        # Check second person
        person2 = people[1]
        assert person2.id == "I0002"
        assert person2.given_names == "Maria Elisabeth"
        assert person2.tussenvoegsel == ""
        assert person2.surname == "de Jong"
        assert person2.birth_date == "2 JUL 1855"
        assert person2.birth_place == "Utrecht"
        assert person2.confidence_score == 0.8

    @patch('web_app.services.gedcom_service.DutchNameParser')
    @patch('web_app.services.gedcom_service.DutchDateParser')
    def test_load_llm_data_missing_fields(self, mock_date_parser, mock_name_parser):
        """Test loading data with missing fields"""
        mock_name_parser.parse_full_name.return_value = ("John", "", "Doe")
        mock_date_parser.parse_dutch_date.return_value = ""

        minimal_data = {"people": [{"given_names": "John"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(minimal_data, f)
            temp_path = f.name

        try:
            generator = LLMGEDCOMGenerator(temp_path)
            people = generator.load_llm_data()

            assert len(people) == 1
            person = people[0]
            assert person.given_names == "John"
            assert person.surname == "Doe"
            assert person.birth_place == ""
            assert person.notes == ""
            assert person.confidence_score == 0.0
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('web_app.services.gedcom_service.DutchNameParser')
    @patch('web_app.services.gedcom_service.DutchDateParser')
    def test_load_llm_data_invalid_json(self, mock_date_parser, mock_name_parser):
        """Test loading invalid JSON data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            generator = LLMGEDCOMGenerator(temp_path)
            # This should raise a JSONDecodeError since the code doesn't handle it
            with pytest.raises(json.JSONDecodeError):
                generator.load_llm_data()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator.load_llm_data')
    def test_generate_gedcom_no_people(self, mock_load_data):
        """Test GEDCOM generation with no people"""
        mock_load_data.return_value = []

        generator = LLMGEDCOMGenerator("test.json")

        # Mock the gedcom writer
        generator.gedcom_writer.generate = Mock(return_value="0 HEAD\n1 CHAR UTF-8\n0 TRLR")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_path = f.name

        try:
            result = generator.generate_gedcom(temp_path)

            assert result["people"] == 0
            assert result["output_file"] == temp_path
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator.load_llm_data')
    def test_generate_gedcom_with_people(self, mock_load_data):
        """Test GEDCOM generation with people"""
        # Create mock people
        mock_person1 = Mock()
        mock_person2 = Mock()
        mock_load_data.return_value = [mock_person1, mock_person2]

        generator = LLMGEDCOMGenerator("test.json")

        # Mock the gedcom writer
        generator.gedcom_writer.add_person = Mock()
        generator.gedcom_writer.generate = Mock(return_value="0 HEAD\n1 CHAR UTF-8\n0 TRLR")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_path = f.name

        try:
            result = generator.generate_gedcom(temp_path)

            # Verify people were added to writer
            assert generator.gedcom_writer.add_person.call_count == 2
            generator.gedcom_writer.add_person.assert_any_call(mock_person1)
            generator.gedcom_writer.add_person.assert_any_call(mock_person2)

            # Verify result
            assert result["people"] == 2
            assert result["output_file"] == temp_path
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGedcomService:
    """Test GedcomService class"""

    @pytest.fixture
    def service(self):
        """Create test service"""
        return GedcomService()

    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service.logger is not None

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_success(self, mock_generator_class, service):
        """Test successful GEDCOM generation"""
        # Mock generator instance
        mock_generator = Mock()
        mock_generator.generate_gedcom.return_value = {"people": 5, "output_file": "test.ged"}
        mock_generator_class.return_value = mock_generator

        # Mock progress callback
        progress_callback = Mock()

        result = service.generate_gedcom(
            input_file="custom_input.json",
            output_file="custom_output.ged",
            progress_callback=progress_callback
        )

        # Verify generator was created correctly
        mock_generator_class.assert_called_once_with("custom_input.json")

        # Verify progress callbacks were called
        assert progress_callback.call_count == 3
        progress_callback.assert_any_call({"status": "starting", "message": "Initializing GEDCOM generator"})
        progress_callback.assert_any_call({"status": "running", "message": "Processing family data"})
        progress_callback.assert_any_call({"status": "completed", "results": {"people": 5, "output_file": "test.ged"}})

        # Verify generate_gedcom was called with output file
        mock_generator.generate_gedcom.assert_called_once_with("custom_output.ged")

        # Verify result
        assert result["success"] is True
        assert result["message"] == "GEDCOM generation completed"
        assert result["output_file"] == "custom_output.ged"
        assert result["results"]["people"] == 5

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_default_files(self, mock_generator_class, service):
        """Test GEDCOM generation with default file names"""
        mock_generator = Mock()
        mock_generator.generate_gedcom.return_value = {"people": 3}
        mock_generator_class.return_value = mock_generator

        result = service.generate_gedcom()

        # Verify default files were used
        mock_generator_class.assert_called_once_with("pdf_processing/llm_genealogy_results.json")

        assert result["success"] is True
        assert result["output_file"] == "family_genealogy.ged"

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_without_progress_callback(self, mock_generator_class, service):
        """Test GEDCOM generation without progress callback"""
        mock_generator = Mock()
        mock_generator.generate_gedcom.return_value = {"people": 2}
        mock_generator_class.return_value = mock_generator

        result = service.generate_gedcom()

        # Should complete successfully without progress callbacks
        assert result["success"] is True

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_error(self, mock_generator_class, service):
        """Test GEDCOM generation with error"""
        # Mock generator to raise exception
        mock_generator_class.side_effect = Exception("File not found")

        progress_callback = Mock()

        result = service.generate_gedcom(progress_callback=progress_callback)

        # Verify error was handled
        assert result["success"] is False
        assert "File not found" in result["error"]

        # Verify error callback was called
        progress_callback.assert_any_call({"status": "failed", "error": "GEDCOM generation failed: File not found"})

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_generator_error(self, mock_generator_class, service):
        """Test GEDCOM generation when generator.generate() fails"""
        mock_generator = Mock()
        mock_generator.generate_gedcom.side_effect = Exception("Generation failed")
        mock_generator_class.return_value = mock_generator

        result = service.generate_gedcom()

        assert result["success"] is False
        assert "Generation failed" in result["error"]

    def test_generate_gedcom_partial_parameters(self, service):
        """Test generation with only some parameters specified"""
        with patch('web_app.services.gedcom_service.LLMGEDCOMGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = {"people": 1}
            mock_generator_class.return_value = mock_generator

            # Test with only input file specified
            result = service.generate_gedcom(input_file="custom.json")
            mock_generator_class.assert_called_once_with("custom.json")

            # Reset mock
            mock_generator_class.reset_mock()

            # Test with only output file specified
            result = service.generate_gedcom(output_file="custom.ged")
            mock_generator_class.assert_called_once_with("pdf_processing/llm_genealogy_results.json")

    def test_service_error_handling_with_none_callback(self, service):
        """Test error handling when progress callback is None"""
        with patch('web_app.services.gedcom_service.LLMGEDCOMGenerator') as mock_generator_class:
            mock_generator_class.side_effect = Exception("Test error")

            result = service.generate_gedcom(progress_callback=None)

            assert result["success"] is False
            assert "Test error" in result["error"]

    @patch('web_app.services.gedcom_service.LLMGEDCOMGenerator')
    def test_generate_gedcom_empty_results(self, mock_generator_class, service):
        """Test generation with empty results"""
        mock_generator = Mock()
        mock_generator.generate_gedcom.return_value = {}
        mock_generator_class.return_value = mock_generator

        result = service.generate_gedcom()

        assert result["success"] is True
        assert result["results"] == {}
