"""
Celery tasks for LLM extraction
"""
import os
from pathlib import Path

from celery import current_task
from celery.exceptions import Retry

from web_app.pdf_processing.llm_genealogy_extractor import LLMGenealogyExtractor
from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.services.prompt_service import PromptService
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.celery_app import celery_app


logger = get_project_logger(__name__)


class ExtractionTaskManager:
    """Manages the extraction workflow with proper error handling"""

    def __init__(self, text_file: str = None):
        self.text_file = self._get_text_file_path(text_file)
        self.extractor = None
        self.chunks = []
        self.all_families = []
        self.all_isolated_individuals = []

    def _get_text_file_path(self, text_file: str = None) -> Path:
        """Get and validate text file path"""
        if not text_file:
            text_file = "web_app/pdf_processing/extracted_text/consolidated_text.txt"

        text_file_path = Path(text_file)
        if not text_file_path.exists():
            raise FileNotFoundError(f"Text file not found: {text_file_path}")

        return text_file_path

    def _create_extractor(self) -> LLMGenealogyExtractor:
        """Create and configure the LLM extractor"""
        return LLMGenealogyExtractor(
            text_file=str(self.text_file),
            ollama_host=os.environ.get('OLLAMA_HOST', '192.168.1.234'),
            ollama_port=int(os.environ.get('OLLAMA_PORT', 11434)),
            ollama_model=os.environ.get('OLLAMA_MODEL', 'aya:35b-23')
        )

    def _load_and_split_text(self):
        """Load text file and split into chunks"""
        try:
            with open(self.text_file, encoding='utf-8') as f:
                content = f.read()

            self.chunks = self.extractor.split_text_intelligently(content)
            logger.info(f"Split text into {len(self.chunks)} chunks")

        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Failed to read text file {self.text_file}: {e}")
            raise

    def _get_active_prompt(self):
        """Get the active prompt for extraction"""
        try:
            prompt_service = PromptService()
            return prompt_service.get_active_prompt()
        except Exception as e:
            logger.warning(f"Failed to get active prompt, using default: {e}")
            return None

    def _process_chunk(self, chunk_index: int, chunk_text: str, active_prompt):
        """Process a single chunk and return extracted data"""
        try:
            if active_prompt:
                chunk_data = self.extractor.extract_from_chunk(chunk_text, custom_prompt=active_prompt.prompt_text)
            else:
                chunk_data = self.extractor.extract_from_chunk(chunk_text)

            return self._add_chunk_metadata(chunk_data, chunk_index)

        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_index + 1}: {e}")
            # Return empty data for this chunk instead of failing the entire task
            return {"families": [], "isolated_individuals": []}

    def _add_chunk_metadata(self, chunk_data: dict, chunk_index: int) -> dict:
        """Add chunk metadata to extracted data"""
        # Add metadata to families
        for family in chunk_data.get("families", []):
            family['chunk_id'] = chunk_index
            family['extraction_method'] = 'llm'
            # Add metadata to family members
            if 'parents' in family:
                if 'father' in family['parents'] and family['parents']['father']:
                    family['parents']['father']['chunk_id'] = chunk_index
                if 'mother' in family['parents'] and family['parents']['mother']:
                    family['parents']['mother']['chunk_id'] = chunk_index
            for child in family.get('children', []):
                child['chunk_id'] = chunk_index

        # Add metadata to isolated individuals
        for person in chunk_data.get("isolated_individuals", []):
            person['chunk_id'] = chunk_index
            person['extraction_method'] = 'llm'

        return chunk_data

    def _save_to_database(self) -> dict:
        """Save extracted data to database"""
        try:
            repository = GenealogyDataRepository()
            return repository.save_extraction_data(self.all_families, self.all_isolated_individuals)
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            raise


    def run_extraction(self):
        """Run the complete extraction workflow"""
        # Initialize
        current_task.update_state(
            state='RUNNING',
            meta={'status': 'initializing', 'progress': 0}
        )

        self.extractor = self._create_extractor()
        self._load_and_split_text()

        current_task.update_state(
            state='RUNNING',
            meta={
                'status': 'processing',
                'progress': 5,
                'total_chunks': len(self.chunks),
                'current_chunk': 0
            }
        )

        # Get active prompt once
        active_prompt = self._get_active_prompt()

        # Process chunks
        for i, chunk in enumerate(self.chunks):
            current_chunk = i + 1
            progress = int((i / len(self.chunks)) * 85) + 5  # 5-90% for processing

            logger.info(f"Processing chunk {current_chunk}/{len(self.chunks)}")

            current_task.update_state(
                state='RUNNING',
                meta={
                    'status': 'processing',
                    'progress': progress,
                    'total_chunks': len(self.chunks),
                    'current_chunk': current_chunk
                }
            )

            chunk_data = self._process_chunk(i, chunk, active_prompt)
            self.all_families.extend(chunk_data.get("families", []))
            self.all_isolated_individuals.extend(chunk_data.get("isolated_individuals", []))

        # Save to database
        current_task.update_state(
            state='RUNNING',
            meta={
                'status': 'saving',
                'progress': 95,
                'total_chunks': len(self.chunks),
                'current_chunk': len(self.chunks)
            }
        )

        save_result = self._save_to_database()

        # Return results
        return {
            'success': True,
            'total_families': len(self.all_families),
            'total_isolated_individuals': len(self.all_isolated_individuals),
            'total_people': self._count_total_people(),
            'families_created': save_result['families_created'],
            'people_created': save_result['people_created'],
            'places_created': save_result['places_created'],
            'summary': self._calculate_summary()
        }

    def _calculate_summary(self) -> dict:
        """Calculate extraction summary statistics"""
        total_people = self._count_total_people()
        total_children = sum(len(f.get('children', [])) for f in self.all_families)
        families_with_parents = sum(1 for f in self.all_families
                                  if f.get('parents', {}).get('father') or f.get('parents', {}).get('mother'))
        families_with_generation = sum(1 for f in self.all_families if f.get('generation_number'))

        return {
            'total_families': len(self.all_families),
            'total_isolated_individuals': len(self.all_isolated_individuals),
            'total_people': total_people,
            'avg_children_per_family': total_children / len(self.all_families) if self.all_families else 0,
            'families_with_parents': families_with_parents,
            'families_with_generation': families_with_generation
        }

    def _count_total_people(self) -> int:
        """Count total number of people across all families and isolated individuals"""
        total_people = sum(len(f.get('children', [])) for f in self.all_families)
        total_people += sum(1 for f in self.all_families if f.get('parents', {}).get('father'))
        total_people += sum(1 for f in self.all_families if f.get('parents', {}).get('mother'))
        total_people += len(self.all_isolated_individuals)
        return total_people


@celery_app.task(bind=True, autoretry_for=(ConnectionError, IOError), retry_kwargs={'max_retries': 3, 'countdown': 60})
def extract_genealogy_data(self, text_file: str = None):
    """
    Extract genealogy data from text using LLM
    
    Args:
        text_file: Path to text file (optional, defaults to consolidated_text.txt)
        
    Returns:
        dict: Extraction results with summary statistics
    """
    task_manager = ExtractionTaskManager(text_file)

    try:
        result = task_manager.run_extraction()
        logger.info(f"Extraction completed successfully: {result}")
        return result

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'File not found: {str(e)}'}
        )
        raise

    except ConnectionError as e:
        logger.error(f"Connection error (will retry): {e}")
        current_task.update_state(
            state='RETRY',
            meta={'status': 'retrying', 'error': f'Connection error: {str(e)}'}
        )
        raise Retry(f"Connection error: {e}")

    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}", exc_info=True)
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'failed', 'error': f'Unexpected error: {str(e)}'}
        )
        raise
