"""
Shared extraction service for both CLI and web interface
"""

import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from flask import current_app

from web_app.pdf_processing.llm_genealogy_extractor import LLMGenealogyExtractor
from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.services.prompt_service import prompt_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

class ExtractionTask:
    """Represents a running extraction task"""
    def __init__(self, task_id: str, extractor: LLMGenealogyExtractor):
        self.id = task_id
        self.extractor = extractor
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
            if self.status == 'running':
                elapsed = datetime.now() - self.start_time
                data['elapsed_seconds'] = int(elapsed.total_seconds())

        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
            if self.start_time:
                duration = self.end_time - self.start_time
                data['duration_seconds'] = int(duration.total_seconds())

        return data

class ExtractionService:
    """Service for managing LLM extraction tasks"""

    def __init__(self):
        self.tasks: dict[str, ExtractionTask] = {}
        self.logger = get_project_logger(__name__)

    def start_extraction(self, text_file: str = None, progress_callback: Callable = None) -> str:
        """Start a new extraction task"""
        task_id = str(uuid.uuid4())

        # Create extractor with configuration
        text_file = text_file or "web_app/pdf_processing/extracted_text/consolidated_text.txt"
        extractor = LLMGenealogyExtractor(
            text_file=text_file,
            ollama_host=current_app.config.get('OLLAMA_HOST', '192.168.1.234'),
            ollama_port=current_app.config.get('OLLAMA_PORT', 11434),
            ollama_model=current_app.config.get('OLLAMA_MODEL', 'aya:35b-23')
        )

        # Create task
        task = ExtractionTask(task_id, extractor)
        self.tasks[task_id] = task

        # Start extraction in background thread
        thread = threading.Thread(
            target=self._run_extraction,
            args=(task, progress_callback),
            daemon=True
        )
        thread.start()

        return task_id

    def get_task(self, task_id: str) -> ExtractionTask | None:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def get_task_status(self, task_id: str) -> dict | None:
        """Get task status as dictionary"""
        task = self.get_task(task_id)
        return task.to_dict() if task else None

    def _run_extraction(self, task: ExtractionTask, progress_callback: Callable = None):
        """Run extraction in background thread"""
        try:
            task.status = 'running'
            task.start_time = datetime.now()

            if progress_callback:
                progress_callback(task.to_dict())

            # Check if text file exists
            if not task.extractor.text_file.exists():
                task.status = 'failed'
                task.error = f"Text file not found: {task.extractor.text_file}"
                task.end_time = datetime.now()
                if progress_callback:
                    progress_callback(task.to_dict())
                return

            # Read and split text
            with open(task.extractor.text_file, encoding='utf-8') as f:
                content = f.read()

            chunks = task.extractor.split_text_intelligently(content)
            task.total_chunks = len(chunks)

            if progress_callback:
                progress_callback(task.to_dict())

            all_families = []
            all_isolated_individuals = []

            for i, chunk in enumerate(chunks):
                task.current_chunk = i + 1
                task.progress = int((i / len(chunks)) * 100)

                self.logger.info(f"Processing chunk {i+1}/{len(chunks)}")

                if progress_callback:
                    progress_callback(task.to_dict())

                # Get active prompt from database
                active_prompt = prompt_service.get_active_prompt()
                if active_prompt:
                    chunk_data = task.extractor.extract_from_chunk(chunk, custom_prompt=active_prompt.prompt_text)
                else:
                    chunk_data = task.extractor.extract_from_chunk(chunk)

                # Add chunk metadata to families
                for family in chunk_data.get("families", []):
                    family['chunk_id'] = i
                    family['extraction_method'] = 'llm'
                    # Add chunk metadata to family members
                    if 'parents' in family:
                        if 'father' in family['parents'] and family['parents']['father']:
                            family['parents']['father']['chunk_id'] = i
                        if 'mother' in family['parents'] and family['parents']['mother']:
                            family['parents']['mother']['chunk_id'] = i
                    for child in family.get('children', []):
                        child['chunk_id'] = i

                # Add chunk metadata to isolated individuals
                for person in chunk_data.get("isolated_individuals", []):
                    person['chunk_id'] = i
                    person['extraction_method'] = 'llm'

                all_families.extend(chunk_data.get("families", []))
                all_isolated_individuals.extend(chunk_data.get("isolated_individuals", []))

                # Small delay to be nice to the LLM
                import time
                time.sleep(1)

            # Store results
            task.extractor.results = {
                "families": all_families,
                "isolated_individuals": all_isolated_individuals
            }

            # Calculate summary
            task.summary = self._calculate_summary(all_families, all_isolated_individuals)

            # Save results to database
            self._save_to_database(all_families, all_isolated_individuals)

            # Also save as JSON for backward compatibility
            task.extractor.save_results()

            task.status = 'completed'
            task.progress = 100
            task.result = {
                'success': True,
                'total_families': len(all_families),
                'total_isolated_individuals': len(all_isolated_individuals),
                'total_people': self._count_total_people(all_families, all_isolated_individuals)
            }

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            task.status = 'failed'
            task.error = str(e)
        finally:
            task.end_time = datetime.now()
            if progress_callback:
                progress_callback(task.to_dict())

    def _calculate_summary(self, families: list[dict], isolated_individuals: list[dict]) -> dict:
        """Calculate extraction summary statistics"""
        total_people = self._count_total_people(families, isolated_individuals)
        total_children = sum(len(f.get('children', [])) for f in families)
        families_with_parents = sum(1 for f in families if f.get('parents', {}).get('father') or f.get('parents', {}).get('mother'))
        families_with_generation = sum(1 for f in families if f.get('generation_number'))

        return {
            'total_families': len(families),
            'total_isolated_individuals': len(isolated_individuals),
            'total_people': total_people,
            'avg_children_per_family': total_children / len(families) if families else 0,
            'families_with_parents': families_with_parents,
            'families_with_generation': families_with_generation
        }

    def _count_total_people(self, families: list[dict], isolated_individuals: list[dict]) -> int:
        """Count total number of people across all families and isolated individuals"""
        total_people = sum(len(f.get('children', [])) for f in families)
        total_people += sum(1 for f in families if f.get('parents', {}).get('father'))
        total_people += sum(1 for f in families if f.get('parents', {}).get('mother'))
        total_people += len(isolated_individuals)
        return total_people

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove old completed/failed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []

        for task_id, task in self.tasks.items():
            if (task.status in ['completed', 'failed'] and
                task.end_time and task.end_time < cutoff_time):
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            self.logger.info(f"Cleaned up old task: {task_id}")

    def _save_to_database(self, families: list[dict], isolated_individuals: list[dict]):
        """Save extracted data to database models"""
        try:
            repository = GenealogyDataRepository()
            result = repository.save_extraction_data(families, isolated_individuals)
            self.logger.info(f"Saved {result['families_created']} families and {result['people_created']} individuals to database")
        except Exception as e:
            self.logger.error(f"Failed to save to database: {e}")
            raise

    def _clear_extraction_data(self):
        """Clear existing extraction data (for fresh extractions)"""
        repository = GenealogyDataRepository()
        repository.clear_all_data()
        self.logger.info("Cleared existing extraction data")




    def get_database_stats(self) -> dict:
        """Get current database statistics"""
        try:
            repository = GenealogyDataRepository()
            stats = repository.get_database_stats()

            # Convert to match expected format and add total
            return {
                'persons': stats['total_people'],
                'families': stats['total_families'],
                'places': stats['total_places'],
                'events': stats['total_events'],
                'marriages': stats['total_marriages'],
                'total_entities': sum(stats.values())
            }
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {}

# Global service instance
extraction_service = ExtractionService()
