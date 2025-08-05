"""
Test utilities and mock objects
"""
from web_app.shared.logging_config import get_project_logger


class MockTaskProgressRepository:
    """Mock repository for testing - doesn't call Celery APIs"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.logger = get_project_logger(self.__class__.__name__)
        self.progress_updates = []  # Track updates for testing
    
    def update_progress(self, status: str, progress: int, **kwargs):
        """Mock progress update that just logs and tracks"""
        update = {'status': status, 'progress': progress, **kwargs}
        self.progress_updates.append(update)
        self.logger.info(f"Task {self.task_id}: {status} ({progress}%)")