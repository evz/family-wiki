"""
Tests for genealogy model benchmark functionality
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from app import create_app
from web_app.pdf_processing.genealogy_model_benchmark import GenealogyModelBenchmark


class TestConfig:
    """Test configuration"""
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    OLLAMA_HOST = 'localhost'
    OLLAMA_PORT = 11434
    OLLAMA_MODEL = 'test-model'

    @property
    def ollama_base_url(self):
        """Construct full Ollama URL"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"


@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app(TestConfig)
    return app


class TestGenealogyModelBenchmark:
    """Test genealogy model benchmark functionality"""

    def test_initialization(self, app):
        """Test benchmark initialization"""
        with app.app_context():
            benchmark = GenealogyModelBenchmark()

            assert len(benchmark.test_cases) == 3
            assert len(benchmark.models_to_test) == 5
            assert benchmark.results == {}

            # Check test cases structure
            for test_case in benchmark.test_cases:
                assert 'name' in test_case
                assert 'text' in test_case
                assert 'expected_people' in test_case
                assert isinstance(test_case['expected_people'], int)
                assert test_case['expected_people'] > 0

    def test_test_cases_content(self, app):
        """Test test cases have expected content"""
        with app.app_context():
            benchmark = GenealogyModelBenchmark()

        # First test case
        test_case = benchmark.test_cases[0]
        assert test_case['name'] == "Dutch names with dates"
        assert "TWEEDE GENERATIE" in test_case['text']
        assert "Arieken Gerritsen" in test_case['text']
        assert test_case['expected_people'] == 2

        # Second test case
        test_case = benchmark.test_cases[1]
        assert test_case['name'] == "Complex family entry"
        assert "Leendert van Zanten" in test_case['text']
        assert test_case['expected_people'] == 2

        # Third test case
        test_case = benchmark.test_cases[2]
        assert test_case['name'] == "Multiple siblings"
        assert "IV.3. Kinderen van" in test_case['text']
        assert test_case['expected_people'] == 3

    def test_models_to_test_list(self, app):
        """Test models list is properly configured"""
        with app.app_context():
            benchmark = GenealogyModelBenchmark()

        expected_models = [
            "qwen2.5:7b",
            "qwen2.5:3b",
            "llama3.2:3b",
            "llama3.1:8b",
            "mistral:7b"
        ]

        assert benchmark.models_to_test == expected_models

    @patch('requests.get')
    def test_check_ollama_running_success(self, mock_get):
        """Test Ollama running check when service is available"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        result = benchmark.check_ollama_running()

        assert result is True
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)

    @patch('requests.get')
    def test_check_ollama_running_failure(self, mock_get):
        """Test Ollama running check when service is not available"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        benchmark = GenealogyModelBenchmark()
        result = benchmark.check_ollama_running()

        assert result is False
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)

    @patch('requests.get')
    def test_check_ollama_running_error_status(self, mock_get):
        """Test Ollama running check with error status"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        result = benchmark.check_ollama_running()

        assert result is False

    @patch('subprocess.run')
    def test_install_model_success(self, mock_run):
        """Test successful model installation"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        benchmark = GenealogyModelBenchmark()
        result = benchmark.install_model("qwen2.5:7b")

        assert result is True
        mock_run.assert_called_once_with(
            ['ollama', 'pull', 'qwen2.5:7b'],
            capture_output=True, text=True, timeout=600
        )

    @patch('subprocess.run')
    def test_install_model_failure(self, mock_run):
        """Test failed model installation"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Model not found"
        mock_run.return_value = mock_result

        benchmark = GenealogyModelBenchmark()
        result = benchmark.install_model("nonexistent:model")

        assert result is False

    @patch('subprocess.run')
    def test_install_model_timeout(self, mock_run):
        """Test model installation timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(['ollama', 'pull'], 600)

        benchmark = GenealogyModelBenchmark()
        result = benchmark.install_model("qwen2.5:7b")

        assert result is False

    @patch('subprocess.run')
    def test_install_model_exception(self, mock_run):
        """Test model installation with exception"""
        mock_run.side_effect = Exception("Subprocess error")

        benchmark = GenealogyModelBenchmark()
        result = benchmark.install_model("qwen2.5:7b")

        assert result is False

    def test_create_genealogy_prompt(self):
        """Test genealogy prompt creation"""
        benchmark = GenealogyModelBenchmark()

        test_text = "Jan Jansen * 1800 Amsterdam"
        prompt = benchmark.create_genealogy_prompt(test_text)

        assert "You are a Dutch genealogy expert" in prompt
        assert "Jan Jansen * 1800 Amsterdam" in prompt
        assert "Return ONLY valid JSON" in prompt
        assert "given_names" in prompt
        assert "surname" in prompt
        assert "birth_date" in prompt
        assert "baptism_date" in prompt
        assert "death_date" in prompt
        assert "marriage_date" in prompt
        assert "confidence" in prompt

    @patch('requests.post')
    def test_test_model_on_case_success(self, mock_post):
        """Test successful model testing on a case"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '{"people": [{"given_names": "Jan", "surname": "Jansen", "confidence": 0.9}]}'
        }
        mock_post.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]

        with patch('time.time', side_effect=[0, 1.5]):  # Mock response time
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert result['success'] is True
        assert result['response_time'] == 1.5
        assert result['people_found'] == 1
        assert result['expected_people'] == 2
        assert result['accuracy_score'] == 0.5  # 1/2 = 0.5
        assert result['json_valid'] is True

    @patch('requests.post')
    def test_test_model_on_case_http_error(self, mock_post):
        """Test model testing with HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]

        with patch('time.time', side_effect=[0, 1.0]):
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert 'error' in result
        assert result['error'] == "HTTP 500"
        assert result['response_time'] == 1.0

    @patch('requests.post')
    def test_test_model_on_case_no_json(self, mock_post):
        """Test model testing with no JSON in response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'This is not JSON format'
        }
        mock_post.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]

        with patch('time.time', side_effect=[0, 1.0]):
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert 'error' in result
        assert result['error'] == "No JSON found in response"
        assert result['response_time'] == 1.0

    @patch('requests.post')
    def test_test_model_on_case_invalid_json(self, mock_post):
        """Test model testing with invalid JSON"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '{"people": [invalid json}'
        }
        mock_post.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]

        with patch('time.time', side_effect=[0, 1.0]):
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert 'error' in result
        assert "Invalid JSON" in result['error']
        assert result['response_time'] == 1.0
        assert result['json_valid'] is False

    @patch('requests.post')
    def test_test_model_on_case_request_exception(self, mock_post):
        """Test model testing with request exception"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]

        with patch('time.time', side_effect=[0, 1.0]):
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert 'error' in result
        assert result['error'] == "Connection failed"

    @patch('requests.post')
    def test_test_model_on_case_perfect_accuracy(self, mock_post):
        """Test model testing with perfect accuracy"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '{"people": [{"given_names": "Jan"}, {"given_names": "Piet"}]}'
        }
        mock_post.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]  # expects 2 people

        with patch('time.time', side_effect=[0, 1.0]):
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert result['success'] is True
        assert result['people_found'] == 2
        assert result['expected_people'] == 2
        assert result['accuracy_score'] == 1.0

    @patch('requests.post')
    def test_test_model_on_case_over_accuracy(self, mock_post):
        """Test model testing with more people found than expected"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '{"people": [{"given_names": "Jan"}, {"given_names": "Piet"}, {"given_names": "Klaas"}]}'
        }
        mock_post.return_value = mock_response

        benchmark = GenealogyModelBenchmark()
        test_case = benchmark.test_cases[0]  # expects 2 people

        with patch('time.time', side_effect=[0, 1.0]):
            result = benchmark.test_model_on_case("qwen2.5:7b", test_case)

        assert result['success'] is True
        assert result['people_found'] == 3
        assert result['expected_people'] == 2
        assert result['accuracy_score'] == 1.0  # Capped at 1.0

    def test_benchmark_model_success(self):
        """Test successful model benchmarking"""
        benchmark = GenealogyModelBenchmark()

        # Mock successful test results
        test_results = [
            {
                'success': True,
                'accuracy_score': 0.8,
                'response_time': 1.0
            },
            {
                'success': True,
                'accuracy_score': 0.9,
                'response_time': 1.2
            },
            {
                'success': False,
                'accuracy_score': 0.0,
                'response_time': 2.0
            }
        ]

        with patch.object(benchmark, 'test_model_on_case', side_effect=test_results):
            with patch('time.sleep'):  # Skip sleep delays
                result = benchmark.benchmark_model("qwen2.5:7b")

        assert result['model'] == "qwen2.5:7b"
        assert len(result['test_cases']) == 3
        assert result['success_rate'] == 2/3  # 2 out of 3 successful
        assert result['avg_response_time'] == 4.2/3  # Average of 1.0, 1.2, 2.0
        assert abs(result['avg_accuracy'] - 1.7/3) < 0.0001  # Total accuracy (0.8 + 0.9 + 0 for failed) / 3 tests
        assert abs(result['overall_score'] - ((2/3) * 0.6 + (1.7/3) * 0.4)) < 0.0001

    def test_benchmark_model_all_failures(self):
        """Test model benchmarking with all failures"""
        benchmark = GenealogyModelBenchmark()

        # Mock failed test results
        test_results = [
            {
                'success': False,
                'error': 'Test error',
                'response_time': 1.0
            },
            {
                'success': False,
                'error': 'Test error',
                'response_time': 1.0
            },
            {
                'success': False,
                'error': 'Test error',
                'response_time': 1.0
            }
        ]

        with patch.object(benchmark, 'test_model_on_case', side_effect=test_results):
            with patch('time.sleep'):
                result = benchmark.benchmark_model("qwen2.5:7b")

        assert result['success_rate'] == 0.0
        assert result['avg_accuracy'] == 0.0
        assert result['overall_score'] == 0.0

    def test_run_full_benchmark_ollama_not_running(self):
        """Test full benchmark when Ollama is not running"""
        benchmark = GenealogyModelBenchmark()

        with patch.object(benchmark, 'check_ollama_running', return_value=False):
            benchmark.run_full_benchmark()

        assert benchmark.results == {}

    def test_run_full_benchmark_success(self):
        """Test successful full benchmark run"""
        benchmark = GenealogyModelBenchmark()

        mock_model_result = {
            'model': 'qwen2.5:7b',
            'overall_score': 0.8,
            'success_rate': 0.9,
            'avg_response_time': 1.5
        }

        with patch.object(benchmark, 'check_ollama_running', return_value=True):
            with patch.object(benchmark, 'install_model', return_value=True):
                with patch.object(benchmark, 'benchmark_model', return_value=mock_model_result):
                    # Test with only first model to speed up test
                    benchmark.models_to_test = ['qwen2.5:7b']
                    benchmark.run_full_benchmark(install_models=True)

        assert 'qwen2.5:7b' in benchmark.results
        assert benchmark.results['qwen2.5:7b'] == mock_model_result

    def test_run_full_benchmark_skip_install(self):
        """Test full benchmark without installing models"""
        benchmark = GenealogyModelBenchmark()

        mock_model_result = {
            'model': 'qwen2.5:7b',
            'overall_score': 0.8,
            'success_rate': 0.9,
            'avg_response_time': 1.5
        }

        with patch.object(benchmark, 'check_ollama_running', return_value=True):
            with patch.object(benchmark, 'benchmark_model', return_value=mock_model_result):
                benchmark.models_to_test = ['qwen2.5:7b']
                benchmark.run_full_benchmark(install_models=False)

        assert 'qwen2.5:7b' in benchmark.results

    def test_run_full_benchmark_install_failure(self):
        """Test full benchmark with model installation failure"""
        benchmark = GenealogyModelBenchmark()

        with patch.object(benchmark, 'check_ollama_running', return_value=True):
            with patch.object(benchmark, 'install_model', return_value=False):
                benchmark.models_to_test = ['qwen2.5:7b']
                benchmark.run_full_benchmark(install_models=True)

        assert benchmark.results == {}

    def test_print_results_no_results(self):
        """Test printing results when no results available"""
        benchmark = GenealogyModelBenchmark()

        # Should not raise exception
        benchmark.print_results()

    def test_print_results_with_results(self):
        """Test printing results with actual results"""
        benchmark = GenealogyModelBenchmark()

        benchmark.results = {
            'qwen2.5:7b': {
                'overall_score': 0.85,
                'success_rate': 0.9,
                'avg_response_time': 1.5,
                'avg_accuracy': 0.8
            },
            'llama3.1:8b': {
                'overall_score': 0.75,
                'success_rate': 0.8,
                'avg_response_time': 2.0,
                'avg_accuracy': 0.7
            }
        }

        # Should not raise exception
        benchmark.print_results()

    def test_save_results(self):
        """Test saving results to file"""
        benchmark = GenealogyModelBenchmark()

        test_results = {
            'qwen2.5:7b': {
                'overall_score': 0.85,
                'success_rate': 0.9,
                'avg_response_time': 1.5
            }
        }
        benchmark.results = test_results

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            benchmark.save_results(output_file)

            # Verify file was created and contains correct data
            with open(output_file) as f:
                saved_data = json.load(f)

            assert saved_data == test_results
        finally:
            Path(output_file).unlink()

    def test_save_results_empty(self):
        """Test saving empty results"""
        benchmark = GenealogyModelBenchmark()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            benchmark.save_results(output_file)

            # Verify file was created and contains empty results
            with open(output_file) as f:
                saved_data = json.load(f)

            assert saved_data == {}
        finally:
            Path(output_file).unlink()

    @patch('builtins.input')
    def test_main_function_proceed(self, mock_input):
        """Test main function when user proceeds"""
        mock_input.return_value = 'y'

        with patch('web_app.pdf_processing.genealogy_model_benchmark.GenealogyModelBenchmark') as mock_benchmark_class:
            mock_benchmark = Mock()
            mock_benchmark_class.return_value = mock_benchmark

            # Import and call main
            from web_app.pdf_processing.genealogy_model_benchmark import main
            main()

            mock_benchmark.run_full_benchmark.assert_called_once_with(install_models=True)
            mock_benchmark.print_results.assert_called_once()
            mock_benchmark.save_results.assert_called_once()

    @patch('builtins.input')
    def test_main_function_cancel(self, mock_input):
        """Test main function when user cancels"""
        mock_input.return_value = 'n'

        with patch('web_app.pdf_processing.genealogy_model_benchmark.GenealogyModelBenchmark') as mock_benchmark_class:
            mock_benchmark = Mock()
            mock_benchmark_class.return_value = mock_benchmark

            # Import and call main
            from web_app.pdf_processing.genealogy_model_benchmark import main
            main()

            # Should not call benchmark methods when cancelled
            mock_benchmark.run_full_benchmark.assert_not_called()
            mock_benchmark.print_results.assert_not_called()
            mock_benchmark.save_results.assert_not_called()

    @patch('builtins.input')
    def test_main_function_invalid_input(self, mock_input):
        """Test main function with invalid input"""
        mock_input.return_value = 'invalid'

        with patch('web_app.pdf_processing.genealogy_model_benchmark.GenealogyModelBenchmark') as mock_benchmark_class:
            mock_benchmark = Mock()
            mock_benchmark_class.return_value = mock_benchmark

            # Import and call main
            from web_app.pdf_processing.genealogy_model_benchmark import main
            main()

            # Should not call benchmark methods with invalid input
            mock_benchmark.run_full_benchmark.assert_not_called()
            mock_benchmark.print_results.assert_not_called()
            mock_benchmark.save_results.assert_not_called()
