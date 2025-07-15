"""
Tests for extraction service
"""

import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app import Config, create_app
from web_app.database.models import Event, Family, Marriage, Person, Place
from web_app.services.extraction_service import ExtractionService, ExtractionTask
from web_app.shared.extraction_task_manager import ExtractionTaskManager


class ExtractionServiceTestConfig(Config):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.TESTING = True
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class TestExtractionTask:
    """Test ExtractionTask class"""

    def test_task_initialization(self):
        """Test task initialization"""
        mock_extractor = Mock()
        task = ExtractionTask("test-123", mock_extractor)

        assert task.id == "test-123"
        assert task.extractor == mock_extractor
        assert task.status == 'pending'
        assert task.progress == 0
        assert task.current_chunk == 0
        assert task.total_chunks == 0
        assert task.start_time is None
        assert task.end_time is None
        assert task.result is None
        assert task.error is None
        assert task.summary is None

    def test_task_to_dict_basic(self):
        """Test task to_dict with basic data"""
        mock_extractor = Mock()
        task = ExtractionTask("test-123", mock_extractor)
        task.status = 'running'
        task.progress = 50

        data = task.to_dict()

        assert data['id'] == "test-123"
        assert data['status'] == 'running'
        assert data['progress'] == 50
        assert data['current_chunk'] == 0
        assert data['total_chunks'] == 0
        assert data['result'] is None
        assert data['error'] is None
        assert data['summary'] is None

    def test_task_to_dict_with_timing(self):
        """Test task to_dict with timing information"""
        mock_extractor = Mock()
        task = ExtractionTask("test-123", mock_extractor)
        task.status = 'running'
        task.start_time = datetime.now()

        data = task.to_dict()

        assert 'start_time' in data
        assert 'elapsed_seconds' in data
        assert isinstance(data['elapsed_seconds'], int)

    def test_task_to_dict_completed(self):
        """Test task to_dict for completed task"""
        mock_extractor = Mock()
        task = ExtractionTask("test-123", mock_extractor)
        task.status = 'completed'
        task.start_time = datetime.now() - timedelta(seconds=60)
        task.end_time = datetime.now()

        data = task.to_dict()

        assert 'start_time' in data
        assert 'end_time' in data
        assert 'duration_seconds' in data
        assert isinstance(data['duration_seconds'], int)


class TestExtractionService:
    """Test ExtractionService class"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app(ExtractionServiceTestConfig)
        return app

    @pytest.fixture
    def service(self, app):
        """Create test service with app context"""
        with app.app_context():
            service = ExtractionService()
            return service

    @pytest.fixture
    def mock_text_file(self):
        """Create a temporary text file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Sample genealogy text content")
            temp_path = f.name

        yield temp_path

        # Cleanup
        import os
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_service_initialization(self, service):
        """Test service initialization"""
        assert isinstance(service.tasks, dict)
        assert len(service.tasks) == 0
        assert service.logger is not None

    @patch('web_app.services.extraction_service.LLMGenealogyExtractor')
    def test_start_extraction_basic(self, mock_extractor_class, service, app):
        """Test basic extraction start"""
        with app.app_context():
            mock_extractor = Mock()
            mock_extractor.text_file.exists.return_value = True
            mock_extractor_class.return_value = mock_extractor

            task_id = service.start_extraction()

            assert task_id in service.tasks
            task = service.tasks[task_id]
            assert isinstance(task, ExtractionTask)
            assert task.extractor == mock_extractor

            # Verify extractor was created with correct parameters
            mock_extractor_class.assert_called_once_with(
                text_file="web_app/pdf_processing/extracted_text/consolidated_text.txt",
                ollama_host='192.168.1.234',
                ollama_port=11434,
                ollama_model='aya:35b-23'
            )

    @patch('web_app.services.extraction_service.LLMGenealogyExtractor')
    def test_start_extraction_custom_text_file(self, mock_extractor_class, service, app):
        """Test extraction with custom text file"""
        with app.app_context():
            mock_extractor = Mock()
            mock_extractor.text_file.exists.return_value = True
            mock_extractor_class.return_value = mock_extractor

            task_id = service.start_extraction(text_file="custom.txt")

            mock_extractor_class.assert_called_once_with(
                text_file="custom.txt",
                ollama_host='192.168.1.234',
                ollama_port=11434,
                ollama_model='aya:35b-23'
            )

    def test_get_task_existing(self, service):
        """Test getting existing task"""
        mock_extractor = Mock()
        task = ExtractionTask("test-123", mock_extractor)
        service.tasks["test-123"] = task

        result = service.get_task("test-123")
        assert result == task

    def test_get_task_nonexistent(self, service):
        """Test getting non-existent task"""
        result = service.get_task("nonexistent")
        assert result is None

    def test_get_task_status_existing(self, service):
        """Test getting status of existing task"""
        mock_extractor = Mock()
        task = ExtractionTask("test-123", mock_extractor)
        task.status = 'running'
        task.progress = 75
        service.tasks["test-123"] = task

        status = service.get_task_status("test-123")

        assert status is not None
        assert status['id'] == "test-123"
        assert status['status'] == 'running'
        assert status['progress'] == 75

    def test_get_task_status_nonexistent(self, service):
        """Test getting status of non-existent task"""
        status = service.get_task_status("nonexistent")
        assert status is None

    def test_cleanup_old_tasks(self, service):
        """Test cleaning up old tasks"""
        mock_extractor = Mock()

        # Create old completed task
        old_task = ExtractionTask("old-task", mock_extractor)
        old_task.status = 'completed'
        old_task.end_time = datetime.now() - timedelta(hours=25)
        service.tasks["old-task"] = old_task

        # Create recent completed task
        recent_task = ExtractionTask("recent-task", mock_extractor)
        recent_task.status = 'completed'
        recent_task.end_time = datetime.now() - timedelta(hours=1)
        service.tasks["recent-task"] = recent_task

        # Create running task (should not be cleaned up)
        running_task = ExtractionTask("running-task", mock_extractor)
        running_task.status = 'running'
        running_task.end_time = datetime.now() - timedelta(hours=25)
        service.tasks["running-task"] = running_task

        service.cleanup_old_tasks(24)

        assert "old-task" not in service.tasks
        assert "recent-task" in service.tasks
        assert "running-task" in service.tasks

    def test_cleanup_old_tasks_custom_age(self, service):
        """Test cleanup with custom max age"""
        mock_extractor = Mock()

        task = ExtractionTask("test-task", mock_extractor)
        task.status = 'failed'
        task.end_time = datetime.now() - timedelta(hours=10)
        service.tasks["test-task"] = task

        # Should not clean up (age < 12 hours)
        service.cleanup_old_tasks(12)
        assert "test-task" in service.tasks

        # Should clean up (age > 8 hours)
        service.cleanup_old_tasks(8)
        assert "test-task" not in service.tasks

    def test_calculate_summary(self, service):
        """Test summary calculation"""
        families = [
            {
                'parents': {'father': {'name': 'John'}, 'mother': {'name': 'Jane'}},
                'children': [{'name': 'Child1'}, {'name': 'Child2'}],
                'generation_number': 1
            },
            {
                'parents': {'father': {'name': 'Bob'}},
                'children': [{'name': 'Child3'}],
                'generation_number': 2
            },
            {
                'parents': {},
                'children': []  # Family with no parents or generation
            }
        ]

        isolated_individuals = [{'name': 'Isolated1'}, {'name': 'Isolated2'}]

        summary = service._calculate_summary(families, isolated_individuals)

        assert summary['total_families'] == 3
        assert summary['total_isolated_individuals'] == 2
        assert summary['total_people'] == 8  # 3 parents + 3 children + 2 isolated
        assert summary['avg_children_per_family'] == 1.0  # 3 children / 3 families
        assert summary['families_with_parents'] == 2
        assert summary['families_with_generation'] == 2

    def test_calculate_summary_empty(self, service):
        """Test summary calculation with empty data"""
        summary = service._calculate_summary([], [])

        assert summary['total_families'] == 0
        assert summary['total_isolated_individuals'] == 0
        assert summary['total_people'] == 0
        assert summary['avg_children_per_family'] == 0
        assert summary['families_with_parents'] == 0
        assert summary['families_with_generation'] == 0

    def test_count_total_people(self, service):
        """Test counting total people"""
        families = [
            {
                'parents': {'father': {'name': 'John'}, 'mother': {'name': 'Jane'}},
                'children': [{'name': 'Child1'}, {'name': 'Child2'}]
            },
            {
                'parents': {'father': {'name': 'Bob'}},
                'children': [{'name': 'Child3'}]
            },
            {
                'parents': {},
                'children': []
            }
        ]

        isolated_individuals = [{'name': 'Isolated1'}, {'name': 'Isolated2'}]

        total = service._count_total_people(families, isolated_individuals)
        assert total == 8  # 2 fathers + 1 mother + 3 children + 2 isolated





    def test_get_database_stats(self, service, app):
        """Test getting database statistics"""
        with app.app_context():
            # Mock the query objects
            with patch.object(Person, 'query') as mock_person_query, \
                 patch.object(Family, 'query') as mock_family_query, \
                 patch.object(Place, 'query') as mock_place_query, \
                 patch.object(Event, 'query') as mock_event_query, \
                 patch.object(Marriage, 'query') as mock_marriage_query:

                mock_person_query.count.return_value = 5
                mock_family_query.count.return_value = 3
                mock_place_query.count.return_value = 10
                mock_event_query.count.return_value = 2
                mock_marriage_query.count.return_value = 1

                stats = service.get_database_stats()

                assert stats['persons'] == 5
                assert stats['families'] == 3
                assert stats['places'] == 10
                assert stats['events'] == 2
                assert stats['marriages'] == 1
                assert stats['total_entities'] == 21

    def test_get_database_stats_error(self, service, app):
        """Test database stats with error"""
        with app.app_context():
            with patch.object(Person, 'query') as mock_person_query:
                mock_person_query.count.side_effect = Exception("Database error")

                stats = service.get_database_stats()

                assert stats == {}



class TestExtractionTaskManager:
    """Test extraction task manager (separated component)"""

    def test_create_and_get_task(self):
        """Test task creation and retrieval"""
        manager = ExtractionTaskManager()
        task_id = manager.create_task()

        assert task_id is not None
        assert len(task_id) == 36  # UUID format

        task = manager.get_task(task_id)
        assert task is not None
        assert task.id == task_id
        assert task.status == 'pending'

    def test_task_lifecycle_methods(self):
        """Test task lifecycle methods"""
        manager = ExtractionTaskManager()
        task_id = manager.create_task()
        task = manager.get_task(task_id)

        # Test start
        task.start(total_chunks=10)
        assert task.status == 'running'
        assert task.total_chunks == 10
        assert task.start_time is not None

        # Test progress update
        task.update_progress(current_chunk=5, progress_percent=50)
        assert task.current_chunk == 5
        assert task.progress == 50

        # Test completion
        result = {'families': 5, 'people': 25}
        summary = {'total_people': 25}
        task.complete(result, summary)

        assert task.status == 'completed'
        assert task.result == result
        assert task.summary == summary
        assert task.progress == 100
        assert task.end_time is not None

    def test_task_failure_handling(self):
        """Test task failure handling"""
        manager = ExtractionTaskManager()
        task_id = manager.create_task()
        task = manager.get_task(task_id)

        task.start()
        task.fail("Test error message")

        assert task.status == 'failed'
        assert task.error == "Test error message"
        assert task.end_time is not None

    def test_get_all_tasks(self):
        """Test getting all tasks"""
        manager = ExtractionTaskManager()

        # Create multiple tasks
        task_id1 = manager.create_task()
        task_id2 = manager.create_task()

        all_tasks = manager.get_all_tasks()

        assert len(all_tasks) == 2
        assert task_id1 in all_tasks
        assert task_id2 in all_tasks
        assert all_tasks[task_id1]['status'] == 'pending'
        assert all_tasks[task_id2]['status'] == 'pending'

    def test_remove_task(self):
        """Test task removal"""
        manager = ExtractionTaskManager()
        task_id = manager.create_task()

        assert manager.get_task(task_id) is not None

        success = manager.remove_task(task_id)
        assert success is True
        assert manager.get_task(task_id) is None

        # Try to remove non-existent task
        success = manager.remove_task('nonexistent')
        assert success is False

    def test_start_extraction_thread(self):
        """Test starting extraction in background thread"""
        manager = ExtractionTaskManager()
        task_id = manager.create_task()

        def mock_extraction_func(task, test_arg):
            task.start(5)
            task.update_progress(2, 40)
            task.complete({'result': test_arg})

        success = manager.start_extraction_thread(task_id, mock_extraction_func, 'test_value')
        assert success is True

        # Wait for thread to complete
        time.sleep(0.1)

        task = manager.get_task(task_id)
        assert task.status == 'completed'
        assert task.result == {'result': 'test_value'}

    def test_nonexistent_task_operations(self):
        """Test operations on nonexistent tasks"""
        manager = ExtractionTaskManager()

        assert manager.get_task('nonexistent') is None
        assert manager.get_task_status('nonexistent') is None
        assert manager.start_extraction_thread('nonexistent', lambda: None) is False
