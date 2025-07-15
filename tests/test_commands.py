"""
Tests for Flask CLI commands
"""

from unittest.mock import patch

import pytest

from app import Config, create_app


class CommandsTestConfig(Config):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.TESTING = True
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class TestCLICommands:
    """Test Flask CLI commands"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app(CommandsTestConfig)
        return app

    @pytest.fixture
    def runner(self, app):
        """Create CLI test runner"""
        return app.test_cli_runner()

    # OCR Command Tests
    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_ocr_command_success(self, mock_processor_class, mock_execute, runner):
        """Test successful OCR command"""
        mock_processor = mock_processor_class.return_value
        mock_execute.return_value = {
            'success': True,
            'results': {'files_processed': 5}
        }

        result = runner.invoke(args=['ocr'])

        assert result.exit_code == 0
        assert '🔍 Starting OCR processing...' in result.output
        assert '✅ OCR processing completed successfully!' in result.output
        mock_processor_class.assert_called_once()
        mock_execute.assert_called_once_with("OCR processing", mock_processor.process_all_pdfs, None)

    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_ocr_command_verbose(self, mock_processor_class, mock_execute, runner):
        """Test OCR command with verbose flag"""
        mock_processor = mock_processor_class.return_value
        mock_execute.return_value = {
            'success': True,
            'results': {'files_processed': 5}
        }

        result = runner.invoke(args=['ocr', '--verbose'])

        assert result.exit_code == 0
        assert 'Results:' in result.output
        # Verify progress callback was passed
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[2] is not None  # progress_callback should not be None

    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_ocr_command_failure(self, mock_processor_class, mock_execute, runner):
        """Test OCR command failure"""
        mock_processor = mock_processor_class.return_value
        mock_execute.return_value = {
            'success': False,
            'error': 'OCR processing failed'
        }

        result = runner.invoke(args=['ocr'])

        assert result.exit_code == 1
        assert '❌ OCR processing failed: OCR processing failed' in result.output

    # Extract Command Tests
    @patch('time.sleep')  # Mock sleep to speed up tests
    @patch('web_app.commands.extraction_service')
    def test_extract_command_success(self, mock_extraction_service, mock_sleep, runner):
        """Test successful extract command"""
        mock_extraction_service.start_extraction.return_value = 'task-123'

        # Mock task status progression
        mock_extraction_service.get_task_status.side_effect = [
            {
                'status': 'running',
                'progress': 50
            },
            {
                'status': 'completed',
                'summary': {
                    'total_families': 5,
                    'total_people': 20,
                    'total_isolated_individuals': 3
                }
            }
        ]

        mock_extraction_service.get_database_stats.return_value = {
            'persons': 20,
            'families': 5,
            'places': 8,
            'total_entities': 33
        }

        result = runner.invoke(args=['extract'])

        assert result.exit_code == 0
        assert '🤖 Starting LLM extraction...' in result.output
        assert '✅ Extraction completed successfully!' in result.output
        assert 'Families: 5' in result.output
        assert 'People: 20' in result.output

    @patch('time.sleep')
    @patch('web_app.commands.extraction_service')
    def test_extract_command_with_text_file(self, mock_extraction_service, mock_sleep, runner):
        """Test extract command with custom text file"""
        mock_extraction_service.start_extraction.return_value = 'task-123'
        mock_extraction_service.get_task_status.return_value = {
            'status': 'completed',
            'summary': {}
        }
        mock_extraction_service.get_database_stats.return_value = {}

        result = runner.invoke(args=['extract', '--text-file', 'custom.txt'])

        assert result.exit_code == 0
        mock_extraction_service.start_extraction.assert_called_once_with(
            text_file='custom.txt',
            progress_callback=None
        )

    @patch('time.sleep')
    @patch('web_app.commands.extraction_service')
    def test_extract_command_task_not_found(self, mock_extraction_service, mock_sleep, runner):
        """Test extract command when task is not found"""
        mock_extraction_service.start_extraction.return_value = 'task-123'
        mock_extraction_service.get_task_status.return_value = None

        result = runner.invoke(args=['extract'])

        assert result.exit_code == 1
        assert '❌ Task not found' in result.output

    @patch('time.sleep')
    @patch('web_app.commands.extraction_service')
    def test_extract_command_failure(self, mock_extraction_service, mock_sleep, runner):
        """Test extract command when extraction fails"""
        mock_extraction_service.start_extraction.return_value = 'task-123'
        mock_extraction_service.get_task_status.return_value = {
            'status': 'failed',
            'error': 'Extraction failed'
        }

        result = runner.invoke(args=['extract'])

        assert result.exit_code == 1
        assert '❌ Extraction failed: Extraction failed' in result.output

    # GEDCOM Command Tests
    @patch('web_app.commands.gedcom_service')
    def test_gedcom_command_success(self, mock_gedcom_service, runner):
        """Test successful GEDCOM command"""
        mock_gedcom_service.generate_gedcom.return_value = {
            'success': True,
            'output_file': 'family.ged',
            'results': {'people': 10}
        }

        result = runner.invoke(args=['gedcom'])

        assert result.exit_code == 0
        assert '📜 Starting GEDCOM generation...' in result.output
        assert '✅ GEDCOM generation completed successfully!' in result.output
        assert '📁 Output file: family.ged' in result.output

    @patch('web_app.commands.gedcom_service')
    def test_gedcom_command_with_options(self, mock_gedcom_service, runner):
        """Test GEDCOM command with input and output options"""
        mock_gedcom_service.generate_gedcom.return_value = {
            'success': True,
            'output_file': 'custom.ged'
        }

        result = runner.invoke(args=['gedcom', '--input-file', 'input.json', '--output-file', 'custom.ged'])

        assert result.exit_code == 0
        mock_gedcom_service.generate_gedcom.assert_called_once_with(
            input_file='input.json',
            output_file='custom.ged',
            progress_callback=None
        )

    @patch('web_app.commands.gedcom_service')
    def test_gedcom_command_failure(self, mock_gedcom_service, runner):
        """Test GEDCOM command failure"""
        mock_gedcom_service.generate_gedcom.return_value = {
            'success': False,
            'error': 'GEDCOM generation failed'
        }

        result = runner.invoke(args=['gedcom'])

        assert result.exit_code == 1
        assert '❌ GEDCOM generation failed: GEDCOM generation failed' in result.output

    # Research Command Tests
    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.ResearchQuestionGenerator')
    def test_research_command_success(self, mock_generator_class, mock_execute, runner):
        """Test successful research command"""
        mock_generator = mock_generator_class.return_value
        mock_execute.return_value = {
            'success': True,
            'results': ['Question 1', 'Question 2', 'Question 3']
        }

        result = runner.invoke(args=['research'])

        assert result.exit_code == 0
        assert '🔬 Starting research question generation...' in result.output
        assert '✅ Research questions generated successfully!' in result.output
        assert '📝 Total questions: 3' in result.output

    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.ResearchQuestionGenerator')
    def test_research_command_verbose(self, mock_generator_class, mock_execute, runner):
        """Test research command with verbose flag and many questions"""
        questions = [f'Question {i}' for i in range(1, 11)]  # 10 questions
        mock_generator = mock_generator_class.return_value
        mock_execute.return_value = {
            'success': True,
            'results': questions
        }

        result = runner.invoke(args=['research', '--verbose'])

        assert result.exit_code == 0
        assert 'Question 1' in result.output
        assert 'Question 5' in result.output
        assert '... and 5 more' in result.output  # Should truncate to first 5

    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.ResearchQuestionGenerator')
    def test_research_command_failure(self, mock_generator_class, mock_execute, runner):
        """Test research command failure"""
        mock_generator = mock_generator_class.return_value
        mock_execute.return_value = {
            'success': False,
            'error': 'Research generation failed'
        }

        result = runner.invoke(args=['research'])

        assert result.exit_code == 1
        assert '❌ Research question generation failed: Research generation failed' in result.output

    # Benchmark Command Tests
    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.GenealogyModelBenchmark')
    def test_benchmark_command_success(self, mock_benchmark_class, mock_execute, runner):
        """Test successful benchmark command"""
        mock_benchmark = mock_benchmark_class.return_value
        mock_execute.return_value = {
            'success': True,
            'results': {'models_tested': 3}
        }

        result = runner.invoke(args=['benchmark'])

        assert result.exit_code == 0
        assert '⚡ Starting model benchmark...' in result.output
        assert '✅ Model benchmark completed successfully!' in result.output

    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.GenealogyModelBenchmark')
    def test_benchmark_command_failure(self, mock_benchmark_class, mock_execute, runner):
        """Test benchmark command failure"""
        mock_benchmark = mock_benchmark_class.return_value
        mock_execute.return_value = {
            'success': False,
            'error': 'Benchmark failed'
        }

        result = runner.invoke(args=['benchmark'])

        assert result.exit_code == 1
        assert '❌ Model benchmark failed: Benchmark failed' in result.output

    # Pipeline Command Tests
    @patch('time.sleep')
    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.ResearchQuestionGenerator')
    @patch('web_app.commands.gedcom_service')
    @patch('web_app.commands.extraction_service')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_pipeline_command_success(self, mock_ocr_class, mock_extraction, mock_gedcom, mock_research_class, mock_execute, mock_sleep, runner):
        """Test successful pipeline command"""
        # Mock all service responses
        mock_ocr = mock_ocr_class.return_value
        mock_research = mock_research_class.return_value

        # Mock execute_with_progress to return success for OCR and research
        def mock_execute_side_effect(operation_name, operation_func, progress_callback=None):
            if "OCR" in operation_name:
                return {'success': True, 'results': {}}
            elif "research" in operation_name:
                return {'success': True, 'results': ['Question 1', 'Question 2']}

        mock_execute.side_effect = mock_execute_side_effect

        mock_extraction.start_extraction.return_value = 'task-123'
        mock_extraction.get_task_status.return_value = {
            'status': 'completed',
            'summary': {'total_families': 5, 'total_people': 20}
        }
        mock_gedcom.generate_gedcom.return_value = {
            'success': True,
            'output_file': 'family.ged'
        }

        result = runner.invoke(args=['pipeline'])

        assert result.exit_code == 0
        assert '🔄 Starting complete pipeline...' in result.output
        assert '📍 Step 1: OCR Processing' in result.output
        assert '📍 Step 2: LLM Extraction' in result.output
        assert '📍 Step 3: GEDCOM Generation' in result.output
        assert '📍 Step 4: Research Questions' in result.output
        assert '🎉 Complete pipeline finished successfully!' in result.output
        assert 'Families extracted: 5' in result.output

    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_pipeline_command_ocr_failure(self, mock_ocr_class, mock_execute, runner):
        """Test pipeline command with OCR failure"""
        mock_ocr = mock_ocr_class.return_value
        mock_execute.return_value = {
            'success': False,
            'error': 'OCR failed'
        }

        result = runner.invoke(args=['pipeline'])

        assert result.exit_code == 1
        assert '❌ Pipeline failed at OCR: OCR failed' in result.output

    @patch('time.sleep')
    @patch('web_app.commands.extraction_service')
    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_pipeline_command_extraction_failure(self, mock_ocr_class, mock_execute, mock_extraction, mock_sleep, runner):
        """Test pipeline command with extraction failure"""
        mock_ocr = mock_ocr_class.return_value
        mock_execute.return_value = {'success': True}
        mock_extraction.start_extraction.return_value = 'task-123'
        mock_extraction.get_task_status.return_value = {
            'status': 'failed',
            'error': 'Extraction failed'
        }

        result = runner.invoke(args=['pipeline'])

        assert result.exit_code == 1
        assert '❌ Pipeline failed at extraction: Extraction failed' in result.output

    # Status Command Tests
    @patch('web_app.commands.extraction_service')
    def test_status_command_all_checks_pass(self, mock_extraction_service, runner):
        """Test status command with database stats"""
        mock_extraction_service.get_database_stats.return_value = {
            'persons': 10,
            'families': 5,
            'places': 8,
            'events': 2,
            'marriages': 3,
            'total_entities': 28
        }

        result = runner.invoke(args=['status'])

        assert result.exit_code == 0
        assert '🔍 Family Wiki Tools Status' in result.output
        assert '🛠️  Available Commands:' in result.output
        assert 'flask ocr' in result.output
        assert '🗄️ Database Statistics:' in result.output
        assert 'Persons: 10' in result.output

    @patch('web_app.commands.extraction_service')
    def test_status_command_no_stats(self, mock_extraction_service, runner):
        """Test status command without database stats"""
        mock_extraction_service.get_database_stats.return_value = {}

        result = runner.invoke(args=['status'])

        assert result.exit_code == 0
        assert '🔍 Family Wiki Tools Status' in result.output
        assert '🛠️  Available Commands:' in result.output

    # Database Clear Command Tests
    @patch('web_app.commands.extraction_service')
    @patch('web_app.database.models.Person')
    @patch('web_app.database.models.Event')
    @patch('web_app.database.models.Marriage')
    @patch('web_app.database.models.Family')
    @patch('web_app.database.db')
    def test_db_clear_command_success(self, mock_db, mock_family, mock_marriage, mock_event, mock_person, mock_extraction_service, runner):
        """Test successful database clear command"""
        # Mock query.delete() for all models
        mock_family.query.delete.return_value = None
        mock_marriage.query.delete.return_value = None
        mock_event.query.delete.return_value = None
        mock_person.query.delete.return_value = None

        mock_extraction_service.get_database_stats.return_value = {
            'total_entities': 0
        }

        result = runner.invoke(args=['db-clear'], input='y\n')

        assert result.exit_code == 0
        assert '🗑️ Clearing database...' in result.output
        assert '✅ Database cleared successfully!' in result.output
        assert 'Remaining entities: 0' in result.output
        mock_db.session.commit.assert_called_once()

    @patch('web_app.commands.extraction_service')
    @patch('web_app.database.models.Family')
    @patch('web_app.database.db')
    def test_db_clear_command_failure(self, mock_db, mock_family, mock_extraction_service, runner):
        """Test database clear command failure"""
        mock_family.query.delete.side_effect = Exception("Database error")

        result = runner.invoke(args=['db-clear'], input='y\n')

        assert result.exit_code == 1
        assert '❌ Failed to clear database: Database error' in result.output

    def test_db_clear_command_cancelled(self, runner):
        """Test database clear command when user cancels"""
        result = runner.invoke(args=['db-clear'], input='n\n')

        assert result.exit_code == 1  # Click confirmation cancellation
        assert 'Aborted' in result.output

    # Verbose Flag Tests
    @patch('web_app.commands.execute_with_progress')
    @patch('web_app.commands.PDFOCRProcessor')
    def test_verbose_flag_provides_progress_callback(self, mock_ocr_class, mock_execute, runner):
        """Test that verbose flag provides progress callback to services"""
        mock_ocr = mock_ocr_class.return_value
        mock_execute.return_value = {'success': True}

        # Test without verbose
        runner.invoke(args=['ocr'])
        args, kwargs = mock_execute.call_args
        assert args[2] is None  # progress_callback should be None

        # Test with verbose
        runner.invoke(args=['ocr', '--verbose'])
        args, kwargs = mock_execute.call_args
        assert args[2] is not None  # progress_callback should not be None

    def test_command_help_text(self, runner):
        """Test that commands have proper help text"""
        result = runner.invoke(args=['ocr', '--help'])
        assert result.exit_code == 0
        assert 'Extract text from PDF files using OCR' in result.output

        result = runner.invoke(args=['extract', '--help'])
        assert result.exit_code == 0
        assert 'Extract genealogical data using AI' in result.output
