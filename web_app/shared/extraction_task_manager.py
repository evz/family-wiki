"""
Extraction task management - separated from business logic
"""

import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class ExtractionTask:
    """Represents a running extraction task"""

    def __init__(self, task_id: str):
        self.id = task_id
        self.status = 'pending'  # pending, running, completed, failed
        self.progress = 0  # 0-100
        self.current_chunk = 0
        self.total_chunks = 0
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self.summary = None

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'status': self.status,
            'progress': self.progress,
            'current_chunk': self.current_chunk,
            'total_chunks': self.total_chunks,
            'result': self.result,
            'error': self.error,
            'summary': self.summary
        }

        # Add timing info
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()

        if self.end_time:
            data['end_time'] = self.end_time.isoformat()

            # Calculate duration
            duration = self.end_time - self.start_time
            data['duration'] = str(duration)

        return data

    def start(self, total_chunks: int = 0):
        """Mark task as started"""
        self.status = 'running'
        self.start_time = datetime.now()
        self.total_chunks = total_chunks
        logger.info(f"Task {self.id} started with {total_chunks} chunks")

    def update_progress(self, current_chunk: int, progress_percent: int):
        """Update task progress"""
        self.current_chunk = current_chunk
        self.progress = progress_percent
        logger.debug(f"Task {self.id} progress: {progress_percent}% (chunk {current_chunk})")

    def complete(self, result: dict, summary: dict = None):
        """Mark task as completed"""
        self.status = 'completed'
        self.end_time = datetime.now()
        self.result = result
        self.summary = summary
        self.progress = 100
        logger.info(f"Task {self.id} completed successfully")

    def fail(self, error: str):
        """Mark task as failed"""
        self.status = 'failed'
        self.end_time = datetime.now()
        self.error = error
        logger.error(f"Task {self.id} failed: {error}")


class ExtractionTaskManager:
    """Manages extraction task lifecycle and threading"""

    def __init__(self):
        self._tasks: dict[str, ExtractionTask] = {}
        self._lock = threading.Lock()

    def create_task(self) -> str:
        """Create a new extraction task"""
        task_id = str(uuid.uuid4())
        with self._lock:
            task = ExtractionTask(task_id)
            self._tasks[task_id] = task

        logger.info(f"Created extraction task: {task_id}")
        return task_id

    def get_task(self, task_id: str) -> ExtractionTask | None:
        """Get a task by ID"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_task_status(self, task_id: str) -> dict | None:
        """Get task status as dictionary"""
        task = self.get_task(task_id)
        return task.to_dict() if task else None

    def start_extraction_thread(self, task_id: str, extraction_func: Callable,
                              *args, **kwargs) -> bool:
        """Start extraction in a background thread"""
        task = self.get_task(task_id)
        if not task:
            return False

        def run_extraction():
            try:
                # Call the extraction function with the task for progress updates
                extraction_func(task, *args, **kwargs)
            except Exception as e:
                task.fail(str(e))
                logger.exception(f"Extraction thread failed for task {task_id}")

        thread = threading.Thread(target=run_extraction, daemon=True)
        thread.start()
        logger.info(f"Started extraction thread for task {task_id}")
        return True

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove old completed/failed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        with self._lock:
            tasks_to_remove = []
            for task_id, task in self._tasks.items():
                # Only remove completed/failed tasks that are old enough
                if (task.status in ['completed', 'failed'] and
                    task.end_time and task.end_time < cutoff_time):
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                logger.debug(f"Cleaned up old task: {task_id}")

            if tasks_to_remove:
                logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

    def get_all_tasks(self) -> dict[str, dict]:
        """Get all tasks as dictionaries"""
        with self._lock:
            return {task_id: task.to_dict() for task_id, task in self._tasks.items()}

    def remove_task(self, task_id: str) -> bool:
        """Remove a specific task"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.info(f"Removed task: {task_id}")
                return True
        return False
