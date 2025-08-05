"""
Tests for genealogy extraction Celery tasks
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from web_app.tasks.extraction_tasks import ExtractionTaskManager, extract_genealogy_data
from tests.test_utils import MockTaskProgressRepository


class TestExtractionTaskManager:
    """Test extraction task manager functionality"""

    @pytest.fixture
    def sample_text_content(self):
        """Sample text content for testing"""
        return """
        Johannes van Berg, born 1820, married Maria de Vries.
        Their children: Pieter (1845), Anna (1847).

        Willem Jansen, farmer, born 1850, died 1920.
        """

    @pytest.fixture
    def temp_text_file(self, sample_text_content):
        """Create temporary text file with sample content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(sample_text_content)
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink()

    @pytest.fixture
    def mock_extractor_class(self):
        """Mock LLMGenealogyExtractor class"""
        with patch('web_app.tasks.extraction_tasks.LLMGenealogyExtractor') as mock:
            yield mock

    @pytest.fixture
    def mock_extractor(self, mock_extractor_class):
        """Mock extractor instance"""
        mock = Mock()
        mock_extractor_class.return_value = mock
        return mock

    @pytest.fixture
    def mock_prompt_service(self):
        """Mock PromptService"""
        with patch('web_app.tasks.extraction_tasks.PromptService') as mock:
            yield mock

    @pytest.fixture
    def mock_repository_class(self):
        """Mock GenealogyDataRepository class"""
        with patch('web_app.tasks.extraction_tasks.GenealogyDataRepository') as mock:
            yield mock

    @pytest.fixture
    def mock_repository(self, mock_repository_class):
        """Mock repository instance"""
        mock = Mock()
        mock_repository_class.return_value = mock
        return mock

    @pytest.fixture
    def mock_current_task(self):
        """Mock current_task"""
        with patch('web_app.tasks.extraction_tasks.current_task') as mock:
            yield mock

    @pytest.fixture
    def mock_logger(self):
        """Mock logger"""
        with patch('web_app.tasks.extraction_tasks.logger') as mock:
            yield mock

    def test_init_default_text_file(self):
        """Test task manager initialization with default text file"""
        with patch.object(Path, 'exists', return_value=True):
            manager = ExtractionTaskManager('test-task-id')
            assert str(manager.text_file) == "web_app/pdf_processing/extracted_text/consolidated_text.txt"
            assert manager.extractor is None
            assert manager.chunks == []
            assert manager.all_families == []
            assert manager.all_isolated_individuals == []

    def test_init_custom_text_file(self, temp_text_file):
        """Test task manager initialization with custom text file"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        assert str(manager.text_file) == temp_text_file

    def test_init_missing_text_file(self):
        """Test task manager initialization with missing text file"""
        with pytest.raises(FileNotFoundError, match="Text file not found"):
            ExtractionTaskManager('test-task-id', "/non/existent/file.txt")

    def test_get_text_file_path_exists(self, temp_text_file):
        """Test getting text file path when file exists"""
        manager = ExtractionTaskManager('test-task-id')
        result = manager._get_text_file_path(temp_text_file)
        assert result == Path(temp_text_file)

    def test_get_text_file_path_not_exists(self):
        """Test getting text file path when file doesn't exist"""
        manager = ExtractionTaskManager.__new__(ExtractionTaskManager)  # Skip __init__
        with pytest.raises(FileNotFoundError, match="Text file not found"):
            manager._get_text_file_path("/non/existent/file.txt")

    def test_create_extractor_default_config(self, temp_text_file, mock_extractor_class):
        """Test creating extractor with default configuration"""
        # Clear environment variables that might affect test
        env_backup = {}
        for key in ['OLLAMA_HOST', 'OLLAMA_PORT', 'OLLAMA_MODEL']:
            env_backup[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]

        try:
            manager = ExtractionTaskManager('test-task-id', temp_text_file)
            manager._create_extractor()

            mock_extractor_class.assert_called_once_with(
                text_file=temp_text_file,
                ollama_host='192.168.1.234',
                ollama_port=11434,
                ollama_model='aya:35b-23'
            )
        finally:
            # Restore environment variables
            for key, value in env_backup.items():
                if value is not None:
                    os.environ[key] = value

    def test_create_extractor_custom_config(self, temp_text_file, mock_extractor_class):
        """Test creating extractor with custom configuration"""
        os.environ['OLLAMA_HOST'] = 'localhost'
        os.environ['OLLAMA_PORT'] = '8080'
        os.environ['OLLAMA_MODEL'] = 'llama2'

        try:
            manager = ExtractionTaskManager('test-task-id', temp_text_file)
            manager._create_extractor()

            mock_extractor_class.assert_called_once_with(
                text_file=temp_text_file,
                ollama_host='localhost',
                ollama_port=8080,
                ollama_model='llama2'
            )
        finally:
            # Clean up environment variables
            for key in ['OLLAMA_HOST', 'OLLAMA_PORT', 'OLLAMA_MODEL']:
                if key in os.environ:
                    del os.environ[key]

    @patch('web_app.services.text_processing_service.TextProcessingService')
    def test_load_and_split_text_success(self, mock_text_processor_class, temp_text_file, mock_extractor):
        """Test successful text loading and splitting with unified processor"""
        # Mock the text processor
        mock_text_processor = Mock()
        mock_text_processor_class.return_value = mock_text_processor

        # Mock enriched chunks from unified processor
        mock_enriched_chunks = [
            {
                'content': 'chunk1',
                'chunk_number': 0,
                'genealogical_context': {'generation_number': 1}
            },
            {
                'content': 'chunk2',
                'chunk_number': 1,
                'genealogical_context': {'generation_number': 2}
            }
        ]
        mock_text_processor.process_corpus_with_anchors.return_value = mock_enriched_chunks

        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.extractor = mock_extractor

        manager._load_and_split_text()

        assert manager.chunks == ["chunk1", "chunk2"]
        assert manager.enriched_chunks == mock_enriched_chunks
        mock_text_processor.process_corpus_with_anchors.assert_called_once()

    def test_load_and_split_text_file_error(self, temp_text_file, mock_extractor, mock_logger):
        """Test text loading with file error"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.extractor = mock_extractor

        with patch('builtins.open', side_effect=OSError("File error")):
            with pytest.raises(OSError):
                manager._load_and_split_text()

        mock_logger.error.assert_called_once()

    def test_load_and_split_text_unicode_error(self, temp_text_file, mock_extractor, mock_logger):
        """Test text loading with unicode error"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.extractor = mock_extractor

        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            with pytest.raises(UnicodeDecodeError):
                manager._load_and_split_text()

        mock_logger.error.assert_called_once()

    def test_get_active_prompt_success(self, temp_text_file, mock_prompt_service):
        """Test getting active prompt successfully"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test prompt"
        mock_service = Mock()
        mock_service.get_active_prompt.return_value = mock_prompt
        mock_prompt_service.return_value = mock_service

        result = manager._get_active_prompt()

        assert result == mock_prompt
        mock_prompt_service.assert_called_once()
        mock_service.get_active_prompt.assert_called_once()

    def test_get_active_prompt_failure(self, temp_text_file, mock_prompt_service, mock_logger):
        """Test getting active prompt with failure"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        mock_service = Mock()
        mock_service.get_active_prompt.side_effect = Exception("Database error")
        mock_prompt_service.return_value = mock_service

        result = manager._get_active_prompt()

        assert result is None
        mock_logger.warning.assert_called_once()

    def test_process_chunk_with_custom_prompt(self, temp_text_file, mock_extractor):
        """Test processing chunk with custom prompt"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.extractor = mock_extractor

        # Set up enriched chunks to simulate unified processor output
        manager.enriched_chunks = [
            {
                'content': 'chunk text',
                'chunk_number': 0,
                'genealogical_context': {
                    'generation_number': 3,
                    'birth_years': [{'year': 1845}],
                    'chunk_type': 'family_group'
                }
            }
        ]

        mock_prompt = Mock()
        mock_prompt.prompt_text = "Custom prompt"

        chunk_data = {
            "families": [{"family_id": "F001", "children": [{"name": "John"}]}],
            "isolated_individuals": [{"name": "Jane"}]
        }
        mock_extractor.extract_from_chunk.return_value = chunk_data

        result = manager._process_chunk(0, "chunk text", mock_prompt)

        # Verify the enhanced chunk text includes context
        called_args = mock_extractor.extract_from_chunk.call_args
        enhanced_text = called_args[0][0]
        assert "Generation 3" in enhanced_text
        assert "Birth years mentioned: 1845" in enhanced_text
        assert "chunk text" in enhanced_text
        assert called_args[1]['custom_prompt'] == "Custom prompt"

        assert result["families"][0]["chunk_id"] == 0
        assert result["isolated_individuals"][0]["chunk_id"] == 0

    def test_process_chunk_without_custom_prompt(self, temp_text_file, mock_extractor):
        """Test processing chunk without custom prompt"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.extractor = mock_extractor

        # Set up enriched chunks without genealogical context
        manager.enriched_chunks = [
            {
                'content': 'chunk text',
                'chunk_number': 0,
                'genealogical_context': {}  # No context
            }
        ]

        chunk_data = {"families": [], "isolated_individuals": []}
        mock_extractor.extract_from_chunk.return_value = chunk_data

        result = manager._process_chunk(0, "chunk text", None)

        # Should be called with just the chunk text (no context to add)
        mock_extractor.extract_from_chunk.assert_called_once_with("chunk text")
        assert result == {"families": [], "isolated_individuals": []}

    def test_process_chunk_exception(self, temp_text_file, mock_extractor, mock_logger):
        """Test processing chunk with exception"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.extractor = mock_extractor
        mock_extractor.extract_from_chunk.side_effect = Exception("Extraction failed")

        result = manager._process_chunk(0, "chunk text", None)

        assert result == {"families": [], "isolated_individuals": []}
        mock_logger.error.assert_called_once()

    def test_add_chunk_metadata_families(self, temp_text_file):
        """Test adding chunk metadata to families"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)

        chunk_data = {
            "families": [{
                "family_id": "F001",
                "parents": {
                    "father": {"name": "John"},
                    "mother": {"name": "Jane"}
                },
                "children": [{"name": "Bob"}, {"name": "Alice"}]
            }],
            "isolated_individuals": [{"name": "William"}]
        }

        result = manager._add_chunk_metadata(chunk_data, 2)

        # Check family metadata
        family = result["families"][0]
        assert family["chunk_id"] == 2
        assert family["extraction_method"] == "llm"
        assert family["parents"]["father"]["chunk_id"] == 2
        assert family["parents"]["mother"]["chunk_id"] == 2
        assert family["children"][0]["chunk_id"] == 2
        assert family["children"][1]["chunk_id"] == 2

        # Check isolated individual metadata
        person = result["isolated_individuals"][0]
        assert person["chunk_id"] == 2
        assert person["extraction_method"] == "llm"

    def test_add_chunk_metadata_empty_parents(self, temp_text_file):
        """Test adding chunk metadata with empty parents"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)

        chunk_data = {
            "families": [{
                "family_id": "F001",
                "parents": {
                    "father": None,
                    "mother": {"name": "Jane"}
                },
                "children": []
            }],
            "isolated_individuals": []
        }

        result = manager._add_chunk_metadata(chunk_data, 1)

        family = result["families"][0]
        assert family["chunk_id"] == 1
        assert family["parents"]["mother"]["chunk_id"] == 1
        # Father is None, so no chunk_id should be added

    def test_save_to_database_success(self, temp_text_file, mock_repository):
        """Test successful database save"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.all_families = [{"family_id": "F001"}]
        manager.all_isolated_individuals = [{"name": "John"}]

        expected_result = {
            'families_created': 1,
            'people_created': 3,
            'places_created': 2
        }
        mock_repository.save_extraction_data.return_value = expected_result

        result = manager._save_to_database()

        assert result == expected_result
        mock_repository.save_extraction_data.assert_called_once_with([{"family_id": "F001"}], [{"name": "John"}])

    def test_save_to_database_failure(self, temp_text_file, mock_repository, mock_logger):
        """Test database save failure"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        mock_repository.save_extraction_data.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            manager._save_to_database()

        mock_logger.error.assert_called_once()

    def test_count_total_people(self, temp_text_file):
        """Test counting total people"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.all_families = [
            {
                "parents": {"father": {"name": "John"}, "mother": {"name": "Jane"}},
                "children": [{"name": "Bob"}, {"name": "Alice"}]
            },
            {
                "parents": {"father": {"name": "Mike"}, "mother": None},
                "children": [{"name": "Sam"}]
            }
        ]
        manager.all_isolated_individuals = [{"name": "William"}, {"name": "Emma"}]

        total = manager._count_total_people()

        # 3 children + 2 fathers + 1 mother + 2 isolated = 8
        assert total == 8

    def test_calculate_summary(self, temp_text_file):
        """Test calculating extraction summary"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.all_families = [
            {
                "parents": {"father": {"name": "John"}, "mother": {"name": "Jane"}},
                "children": [{"name": "Bob"}, {"name": "Alice"}],
                "generation_number": 1
            },
            {
                "parents": {"father": None, "mother": None},
                "children": [{"name": "Sam"}]
            }
        ]
        manager.all_isolated_individuals = [{"name": "William"}]

        summary = manager._calculate_summary()

        assert summary['total_families'] == 2
        assert summary['total_isolated_individuals'] == 1
        assert summary['total_people'] == 6  # 3 children + 1 father + 1 mother + 1 isolated = 6
        assert summary['avg_children_per_family'] == 1.5  # (2 + 1) / 2
        assert summary['families_with_parents'] == 1  # Only first family has parents
        assert summary['families_with_generation'] == 1  # Only first family has generation_number

    def test_calculate_summary_no_families(self, temp_text_file):
        """Test calculating summary with no families"""
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        manager.all_families = []
        manager.all_isolated_individuals = [{"name": "William"}]

        summary = manager._calculate_summary()

        assert summary['total_families'] == 0
        assert summary['total_isolated_individuals'] == 1
        assert summary['avg_children_per_family'] == 0  # No division by zero


class TestExtractionTaskManagerIntegration:
    """Integration tests for ExtractionTaskManager.run()"""

    @pytest.fixture
    def temp_text_file(self):
        """Create temporary text file"""
        content = "Johannes van Berg, born 1820, married Maria de Vries."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
        yield f.name
        Path(f.name).unlink()

    @pytest.fixture
    def mock_extractor_class(self):
        """Mock LLMGenealogyExtractor class"""
        with patch('web_app.tasks.extraction_tasks.LLMGenealogyExtractor') as mock:
            yield mock

    @pytest.fixture
    def mock_extractor(self, mock_extractor_class):
        """Mock extractor instance"""
        mock = Mock()
        mock_extractor_class.return_value = mock
        return mock

    @pytest.fixture
    def mock_prompt_service(self):
        """Mock PromptService"""
        with patch('web_app.tasks.extraction_tasks.PromptService') as mock:
            yield mock

    @pytest.fixture
    def mock_repository_class(self):
        """Mock GenealogyDataRepository class"""
        with patch('web_app.tasks.extraction_tasks.GenealogyDataRepository') as mock:
            yield mock

    @pytest.fixture
    def mock_repository(self, mock_repository_class):
        """Mock repository instance"""
        mock = Mock()
        mock_repository_class.return_value = mock
        return mock

    @pytest.fixture
    def mock_current_task(self):
        """Mock current_task"""
        with patch('web_app.tasks.extraction_tasks.current_task') as mock:
            yield mock

    @pytest.fixture
    def mock_logger(self):
        """Mock logger"""
        with patch('web_app.tasks.extraction_tasks.logger') as mock:
            yield mock

    @patch('web_app.services.text_processing_service.TextProcessingService')
    def test_run_success(self, mock_text_processor_class, temp_text_file, mock_extractor,
                                   mock_prompt_service, mock_repository, mock_current_task, mock_logger):
        """Test successful complete extraction workflow with unified processor"""
        # Mock the text processor
        mock_text_processor = Mock()
        mock_text_processor_class.return_value = mock_text_processor

        # Mock enriched chunks from unified processor
        mock_enriched_chunks = [
            {
                'content': 'chunk1',
                'chunk_number': 0,
                'genealogical_context': {'generation_number': 1}
            },
            {
                'content': 'chunk2',
                'chunk_number': 1,
                'genealogical_context': {'generation_number': 2}
            }
        ]
        mock_text_processor.process_corpus_with_anchors.return_value = mock_enriched_chunks

        # Setup other mocks
        mock_extractor.extract_from_chunk.return_value = {
            "families": [{"family_id": "F001", "children": [{"name": "John"}]}],
            "isolated_individuals": [{"name": "Jane"}]
        }

        mock_service = Mock()
        mock_service.get_active_prompt.return_value = None
        mock_prompt_service.return_value = mock_service

        mock_repository.save_extraction_data.return_value = {
            'families_created': 2,
            'people_created': 4,
            'places_created': 1
        }

        # Run extraction
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        # Override with mock for testing
        manager.progress = MockTaskProgressRepository('test-task-id')
        result = manager.run()

        # Verify results
        assert result['success'] is True
        assert result['total_families'] == 2  # 2 chunks * 1 family each
        assert result['total_isolated_individuals'] == 2  # 2 chunks * 1 individual each
        assert result['families_created'] == 2
        assert result['people_created'] == 4
        assert result['places_created'] == 1

        # Verify progress updates were made (using MockTaskProgressRepository)
        progress_updates = manager.progress.progress_updates
        assert len(progress_updates) >= 4  # initializing, processing, saving, etc.

        # Check specific progress states
        states = [update['status'] for update in progress_updates]
        assert 'initializing' in states
        assert 'processing' in states
        assert 'saving' in states

    @patch('web_app.services.text_processing_service.TextProcessingService')
    def test_run_with_custom_prompt(self, mock_text_processor_class, temp_text_file, mock_extractor,
                                              mock_prompt_service, mock_repository, mock_current_task, mock_logger):
        """Test extraction with custom prompt"""
        # Mock the text processor
        mock_text_processor = Mock()
        mock_text_processor_class.return_value = mock_text_processor

        # Mock enriched chunks from unified processor
        mock_enriched_chunks = [
            {
                'content': 'chunk1',
                'chunk_number': 0,
                'genealogical_context': {}  # No context for simplicity
            }
        ]
        mock_text_processor.process_corpus_with_anchors.return_value = mock_enriched_chunks

        # Setup other mocks
        mock_extractor.extract_from_chunk.return_value = {
            "families": [],
            "isolated_individuals": []
        }

        mock_prompt = Mock()
        mock_prompt.prompt_text = "Custom prompt"
        mock_service = Mock()
        mock_service.get_active_prompt.return_value = mock_prompt
        mock_prompt_service.return_value = mock_service

        mock_repository.save_extraction_data.return_value = {
            'families_created': 0,
            'people_created': 0,
            'places_created': 0
        }

        # Run extraction
        manager = ExtractionTaskManager('test-task-id', temp_text_file)
        # Override with mock for testing
        manager.progress = MockTaskProgressRepository('test-task-id')
        result = manager.run()

        # Verify custom prompt was used
        mock_extractor.extract_from_chunk.assert_called_with("chunk1", custom_prompt="Custom prompt")
        assert result['success'] is True


class TestExtractGenealogyDataTask:
    """Test the main Celery task function"""

    @pytest.fixture
    def temp_text_file(self):
        """Create temporary text file"""
        content = "Test genealogy text content"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
        yield f.name
        Path(f.name).unlink()

    @pytest.fixture
    def mock_task_manager_class(self):
        """Mock ExtractionTaskManager class"""
        with patch('web_app.tasks.extraction_tasks.ExtractionTaskManager') as mock:
            yield mock

    @pytest.fixture
    def mock_task_manager(self, mock_task_manager_class):
        """Mock task manager instance"""
        mock = Mock()
        mock_task_manager_class.return_value = mock
        return mock

    @pytest.fixture
    def mock_current_task(self):
        """Mock current_task"""
        with patch('web_app.tasks.extraction_tasks.current_task') as mock:
            yield mock

    @pytest.fixture
    def mock_logger(self):
        """Mock logger"""
        with patch('web_app.tasks.extraction_tasks.logger') as mock:
            yield mock

    def test_extract_genealogy_data_success(self, temp_text_file, mock_task_manager, mock_current_task, mock_logger):
        """Test successful genealogy data extraction task"""
        expected_result = {
            'success': True,
            'total_families': 2,
            'total_isolated_individuals': 1,
            'total_people': 5
        }
        mock_task_manager.run.return_value = expected_result

        # Call the task using pytest-celery approach
        result = extract_genealogy_data.apply(args=(temp_text_file,))

        # Verify results
        assert result.successful()
        result_data = result.result
        assert result_data == expected_result

        # Verify task manager was called correctly
        mock_task_manager.run.assert_called_once()
        # Logger calls are now handled by BaseFileProcessingTask

    def test_extract_genealogy_data_default_file(self, mock_task_manager, mock_current_task, mock_logger):
        """Test extraction with default text file"""
        expected_result = {'success': True, 'total_people': 0}
        mock_task_manager.run.return_value = expected_result

        # Mock the default file exists
        with patch.object(Path, 'exists', return_value=True):
            result = extract_genealogy_data.apply(args=(None,))

        assert result.successful()
        mock_task_manager.run.assert_called_once()

    def test_extract_genealogy_data_file_not_found(self, mock_task_manager_class, mock_current_task, mock_logger):
        """Test extraction with file not found error (should not retry)"""
        # Setup the task manager constructor to raise FileNotFoundError
        mock_task_manager_class.side_effect = FileNotFoundError("File not found")

        # Call the task
        result = extract_genealogy_data.apply(args=("/non/existent/file.txt",))

        # Verify task failed - just check that it failed and is the right exception type
        assert result.failed()
        # FileNotFoundError should not be retried, so it should fail with the original exception
        assert "File not found" in str(result.result)

    @patch('web_app.tasks.base_task.current_task')
    def test_extract_genealogy_data_connection_error(self, mock_base_current_task, temp_text_file, mock_task_manager, mock_current_task, mock_logger):
        """Test extraction with connection error (should retry)"""
        mock_task_manager.run.side_effect = ConnectionError("Connection failed")

        # Call the task
        result = extract_genealogy_data.apply(args=(temp_text_file,))

        # ConnectionError should be retried, but after max retries it should eventually fail
        assert not result.successful()
        # Error logging is now handled by BaseFileProcessingTask
        mock_base_current_task.update_state.assert_called()

        # Verify the retry behavior was triggered
        retry_calls = [call for call in mock_base_current_task.update_state.call_args_list
                      if call[1]['state'] == 'RETRY']
        assert len(retry_calls) >= 1

    def test_extract_genealogy_data_io_error(self, temp_text_file, mock_task_manager, mock_current_task, mock_logger):
        """Test extraction with IO error (should retry)"""
        mock_task_manager.run.side_effect = OSError("IO error")

        # Call the task
        result = extract_genealogy_data.apply(args=(temp_text_file,))

        # OSError/IOError should be retried, but after max retries it should eventually fail
        assert not result.successful()
        # Just verify it contains the error message
        assert "IO error" in str(result.result)

    @patch('web_app.tasks.base_task.current_task')
    def test_extract_genealogy_data_unexpected_error(self, mock_base_current_task, temp_text_file, mock_task_manager, mock_current_task, mock_logger):
        """Test extraction with unexpected error"""
        mock_task_manager.run.side_effect = RuntimeError("Unexpected error")

        # Call the task
        result = extract_genealogy_data.apply(args=(temp_text_file,))

        # Verify task failed
        assert result.failed()
        assert isinstance(result.result, RuntimeError)

        # Verify error handling - now handled by BaseFileProcessingTask
        mock_base_current_task.update_state.assert_called_with(
            state='FAILURE',
            meta={'status': 'failed', 'error': 'Runtime error: Unexpected error'}
        )

    def test_extract_genealogy_data_progress_updates(self, temp_text_file, mock_task_manager, mock_current_task, mock_logger):
        """Test that progress updates are called during extraction"""
        # Mock the run to simulate progress updates
        def mock_run():
            mock_current_task.update_state(state='RUNNING', meta={'status': 'initializing', 'progress': 0})
            mock_current_task.update_state(state='RUNNING', meta={'status': 'processing', 'progress': 50})
            mock_current_task.update_state(state='RUNNING', meta={'status': 'saving', 'progress': 95})
            return {'success': True, 'total_people': 5}

        mock_task_manager.run.side_effect = mock_run

        # Call the task
        result = extract_genealogy_data.apply(args=(temp_text_file,))

        # Verify results
        assert result.successful()

        # Progress updates are called from within run (mocked above)
        assert mock_current_task.update_state.call_count >= 3

