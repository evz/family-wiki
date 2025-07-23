"""
Tests for research question generation Celery tasks
"""
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from web_app.tasks.research_tasks import generate_research_questions


class TestGenerateResearchQuestionsTask:
    """Test the research questions generation Celery task function"""

    @pytest.fixture
    def task_id(self):
        """Sample task ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_input_data(self):
        """Sample genealogy data for testing"""
        return {
            "families": [
                {
                    "family_id": "F001",
                    "husband": "Johannes van Berg",
                    "wife": "Maria de Vries",
                    "children": ["Pieter van Berg", "Anna van Berg"]
                }
            ],
            "isolated_individuals": [
                {
                    "name": "Willem Jansen",
                    "birth_date": "1850",
                    "occupation": "farmer"
                }
            ]
        }

    @pytest.fixture
    def temp_input_file(self, sample_input_data):
        """Create temporary input file with sample data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_input_data, f)
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink()

    @pytest.fixture
    def mock_generator_class(self):
        """Mock ResearchQuestionGenerator class"""
        with patch('web_app.tasks.research_tasks.ResearchQuestionGenerator') as mock:
            yield mock

    @pytest.fixture
    def mock_current_task(self):
        """Mock current_task"""
        with patch('web_app.tasks.research_tasks.current_task') as mock:
            yield mock

    @pytest.fixture
    def mock_logger(self):
        """Mock logger"""
        with patch('web_app.tasks.research_tasks.logger') as mock:
            yield mock

    @pytest.fixture
    def mock_generator(self, mock_generator_class):
        """Mock generator instance"""
        mock = Mock()
        mock_generator_class.return_value = mock
        return mock

    def test_generate_research_questions_success_no_output_file(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test successful research question generation without output file"""
        mock_questions = [
            "What was Johannes van Berg's birth date?",
            "Where did Maria de Vries live before marriage?"
        ]
        mock_generator.generate_all_questions.return_value = mock_questions

        # Call the task using pytest-celery approach
        result = generate_research_questions.apply(args=(temp_input_file, None))

        # Verify results
        assert result.successful()
        result_data = result.result
        assert result_data['success'] is True
        assert result_data['questions'] == mock_questions
        assert result_data['input_file'] == temp_input_file
        assert result_data['total_questions'] == 2
        assert 'output_file' not in result_data

        # Verify generator was called correctly
        mock_generator.generate_all_questions.assert_called_once()
        mock_logger.info.assert_called_once()
        assert mock_current_task.update_state.call_count >= 4

    def test_generate_research_questions_success_with_output_file(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test successful research question generation with output file"""
        mock_questions = {"research_questions": ["Question 1", "Question 2"]}
        mock_generator.generate_all_questions.return_value = mock_questions

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Call the task
            result = generate_research_questions.apply(args=(temp_input_file, output_path))

            # Verify results
            assert result.successful()
            result_data = result.result
            assert result_data['success'] is True
            assert result_data['questions'] == mock_questions
            assert result_data['input_file'] == temp_input_file
            assert result_data['output_file'] == output_path
            assert result_data['total_questions'] == 0  # dict length

            # Verify file was written
            assert Path(output_path).exists()
            with open(output_path, encoding='utf-8') as f:
                saved_data = json.load(f)
                assert saved_data == mock_questions

            mock_generator.generate_all_questions.assert_called_once()
            mock_logger.info.assert_called_once()
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_research_questions_default_input_file(self, mock_generator, mock_current_task, mock_logger):
        """Test research question generation with default input file"""
        default_input = "web_app/pdf_processing/llm_genealogy_results.json"
        mock_generator.generate_all_questions.return_value = ["Question 1"]

        with patch('web_app.tasks.research_tasks.Path') as mock_path_class:
            # Mock Path behavior
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path.is_file.return_value = True
            mock_path_class.return_value = mock_path

            # Call the task with no input file
            result = generate_research_questions.apply(args=(None, None))

            # Verify default input file was used
            assert result.successful()
            mock_path_class.assert_called_with(default_input)

    def test_generate_research_questions_input_file_not_found(self, mock_current_task, mock_logger):
        """Test research question generation with missing input file"""
        non_existent_file = "/tmp/non_existent_file.json"

        # Call the task
        result = generate_research_questions.apply(args=(non_existent_file, None))

        # Verify task failed - FileNotFoundError is in autoretry_for, so it retries then fails
        assert result.failed()
        assert isinstance(result.result, FileNotFoundError)

        # Verify error handling - called multiple times due to retries
        assert mock_logger.error.call_count >= 1
        assert mock_current_task.update_state.call_count >= 1

    def test_generate_research_questions_input_not_file(self, mock_current_task, mock_logger):
        """Test research question generation when input path is not a file"""
        # Use a directory instead of a file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Call the task
            result = generate_research_questions.apply(args=(temp_dir, None))

            # Verify task failed
            assert result.failed()
            assert isinstance(result.result, ValueError)

            # Verify error handling
            mock_logger.error.assert_called_once()
            mock_current_task.update_state.assert_called_with(
                state='FAILURE',
                meta={'status': 'failed', 'error': f'Invalid input: Input path is not a file: {temp_dir}'}
            )

    def test_generate_research_questions_generator_runtime_error(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test research question generation with generator runtime error"""
        # Setup mock generator to raise RuntimeError
        mock_generator.generate_all_questions.side_effect = RuntimeError("Generation failed")

        # Call the task
        result = generate_research_questions.apply(args=(temp_input_file, None))

        # Verify task failed
        assert result.failed()
        assert isinstance(result.result, RuntimeError)

        # Verify error handling
        mock_logger.error.assert_called_once()
        mock_current_task.update_state.assert_called_with(
            state='FAILURE',
            meta={'status': 'failed', 'error': 'Generation failed'}
        )

    def test_generate_research_questions_output_file_permission_error(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test research question generation with output file permission error"""
        mock_generator.generate_all_questions.return_value = ["Question 1"]

        # Mock file opening to raise PermissionError
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Call the task
            result = generate_research_questions.apply(args=(temp_input_file, "/tmp/output.json"))

            # OSError/PermissionError should be retried, but after max retries it should eventually fail
            assert not result.successful()
            mock_logger.error.assert_called()
            mock_current_task.update_state.assert_called()

            # Verify the retry behavior was triggered
            retry_calls = [call for call in mock_current_task.update_state.call_args_list
                          if call[1]['state'] == 'RETRY']
            assert len(retry_calls) >= 1

    def test_generate_research_questions_output_file_os_error(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test research question generation with output file OS error"""
        mock_generator.generate_all_questions.return_value = ["Question 1"]

        # Mock file opening to raise OSError
        with patch('builtins.open', side_effect=OSError("Disk full")):
            # Call the task
            result = generate_research_questions.apply(args=(temp_input_file, "/tmp/output.json"))

            # OSError should be retried, but after max retries it should eventually fail
            assert not result.successful()
            mock_logger.error.assert_called()
            mock_current_task.update_state.assert_called()

            # Verify the retry behavior was triggered
            retry_calls = [call for call in mock_current_task.update_state.call_args_list
                          if call[1]['state'] == 'RETRY']
            assert len(retry_calls) >= 1

    def test_generate_research_questions_import_error(self, temp_input_file, mock_generator_class, mock_current_task, mock_logger):
        """Test research question generation with import error"""
        # Setup mock generator class to raise ImportError
        mock_generator_class.side_effect = ImportError("Missing dependency")

        # Call the task
        result = generate_research_questions.apply(args=(temp_input_file, None))

        # Verify task failed
        assert result.failed()
        assert isinstance(result.result, ImportError)

        # Verify error handling
        mock_logger.error.assert_called_once()
        mock_current_task.update_state.assert_called_with(
            state='FAILURE',
            meta={'status': 'failed', 'error': 'Missing dependency: Missing dependency'}
        )

    def test_generate_research_questions_string_output(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test research question generation with string output (not JSON)"""
        # Setup mock generator to return string
        mock_questions = "Research questions as string"
        mock_generator.generate_all_questions.return_value = mock_questions

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Call the task
            result = generate_research_questions.apply(args=(temp_input_file, output_path))

            # Verify results
            assert result.successful()
            result_data = result.result
            assert result_data['success'] is True
            assert result_data['questions'] == mock_questions

            # Verify string was written to file
            with open(output_path, encoding='utf-8') as f:
                content = f.read()
                assert content == mock_questions
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_research_questions_list_output(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test research question generation with list output"""
        # Setup mock generator to return list
        mock_questions = ["Question 1", "Question 2", "Question 3"]
        mock_generator.generate_all_questions.return_value = mock_questions

        # Call the task
        result = generate_research_questions.apply(args=(temp_input_file, None))

        # Verify results
        assert result.successful()
        result_data = result.result
        assert result_data['success'] is True
        assert result_data['questions'] == mock_questions
        assert result_data['total_questions'] == 3

    def test_generate_research_questions_progress_updates(self, temp_input_file, mock_generator, mock_current_task, mock_logger):
        """Test that progress updates are called correctly"""
        mock_generator.generate_all_questions.return_value = ["Question 1"]

        # Call the task
        result = generate_research_questions.apply(args=(temp_input_file, None))

        # Verify results
        assert result.successful()

        # Verify progress updates were called
        update_calls = mock_current_task.update_state.call_args_list
        assert len(update_calls) >= 4

        # Check specific progress updates
        progress_values = [call[1]['meta']['progress'] for call in update_calls]
        assert 0 in progress_values  # initializing
        assert 10 in progress_values  # generating
        assert 50 in progress_values  # processing
        assert 90 in progress_values  # saving
