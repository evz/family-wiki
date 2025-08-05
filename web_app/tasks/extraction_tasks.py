"""
Celery tasks for LLM extraction
"""
import os
from pathlib import Path

from celery import current_task

from web_app.pdf_processing.llm_genealogy_extractor import LLMGenealogyExtractor
from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.services.prompt_service import PromptService
from web_app.shared.logging_config import get_project_logger
from web_app.tasks.base_task import BaseTaskManager, BaseFileProcessingTask
from web_app.tasks.celery_app import celery


logger = get_project_logger(__name__)


class ExtractionTaskManager(BaseTaskManager):
    """Manages the extraction workflow with proper error handling"""

    def __init__(self, task_id: str, text_file: str = None):
        super().__init__(task_id)
        self.text_file = self._get_text_file_path(text_file)
        self.extractor = None
        self.chunks = []
        self.enriched_chunks = []
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
        """Load text file and split into chunks using unified processor"""
        try:
            with open(self.text_file, encoding='utf-8') as f:
                content = f.read()

            # Use unified processor for consistent chunking with genealogical anchoring
            from web_app.services.text_processing_service import TextProcessingService
            text_processor = TextProcessingService()

            enriched_chunks = text_processor.process_corpus_with_anchors(
                raw_text=content,
                chunk_size=2000,  # Slightly larger chunks for extraction
                overlap_percentage=0.25,  # More overlap for better entity continuity
                spellfix=True  # Enable spell correction for extraction
            )

            # Store enriched chunks for processing
            self.enriched_chunks = enriched_chunks
            # Keep simple chunks list for compatibility
            self.chunks = [chunk['content'] for chunk in enriched_chunks]

            logger.info(f"Split text into {len(self.chunks)} enriched chunks with genealogical context")

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
        """Process a single chunk with genealogical context and return extracted data"""
        try:
            # Get enriched chunk data if available
            enriched_chunk = getattr(self, 'enriched_chunks', [None])[chunk_index] if hasattr(self, 'enriched_chunks') else None

            if enriched_chunk and enriched_chunk.get('genealogical_context'):
                # Build context-aware prompt
                gen_context = enriched_chunk['genealogical_context']
                context_info = []

                if gen_context.get('generation_number'):
                    context_info.append(f"Generation {gen_context['generation_number']}")
                if gen_context.get('birth_years'):
                    years = [str(by['year']) for by in gen_context['birth_years']]
                    context_info.append(f"Birth years mentioned: {', '.join(years)}")
                if gen_context.get('chunk_type') and gen_context['chunk_type'] != 'general':
                    context_info.append(f"Content type: {gen_context['chunk_type']}")

                if context_info:
                    context_hint = f"CONTEXT: {' | '.join(context_info)}\n\n"
                    enhanced_chunk_text = context_hint + chunk_text
                else:
                    enhanced_chunk_text = chunk_text
            else:
                enhanced_chunk_text = chunk_text

            # Extract with context-enhanced prompt
            if active_prompt:
                chunk_data = self.extractor.extract_from_chunk(enhanced_chunk_text, custom_prompt=active_prompt.prompt_text)
            else:
                chunk_data = self.extractor.extract_from_chunk(enhanced_chunk_text)

            return self._add_chunk_metadata(chunk_data, chunk_index, enriched_chunk)

        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_index + 1}: {e}")
            # Return empty data for this chunk instead of failing the entire task
            return {"families": [], "isolated_individuals": []}

    def _add_chunk_metadata(self, chunk_data: dict, chunk_index: int, enriched_chunk: dict = None) -> dict:
        """Add chunk metadata and genealogical context to extracted data"""
        # Get genealogical context if available
        gen_context = enriched_chunk.get('genealogical_context', {}) if enriched_chunk else {}

        # Add metadata to families
        for family in chunk_data.get("families", []):
            family['chunk_id'] = chunk_index
            family['extraction_method'] = 'llm'
            # Add genealogical context
            if gen_context.get('generation_number'):
                family['generation_number'] = gen_context['generation_number']
            if gen_context.get('birth_years'):
                family['context_birth_years'] = [by['year'] for by in gen_context['birth_years']]

            # Add metadata to family members
            if 'parents' in family:
                if 'father' in family['parents'] and family['parents']['father']:
                    family['parents']['father']['chunk_id'] = chunk_index
                    if gen_context.get('generation_number'):
                        family['parents']['father']['generation_number'] = gen_context['generation_number']
                if 'mother' in family['parents'] and family['parents']['mother']:
                    family['parents']['mother']['chunk_id'] = chunk_index
                    if gen_context.get('generation_number'):
                        family['parents']['mother']['generation_number'] = gen_context['generation_number']
            for child in family.get('children', []):
                child['chunk_id'] = chunk_index
                # Children are typically one generation higher than parents
                if gen_context.get('generation_number'):
                    child['generation_number'] = gen_context['generation_number'] + 1

        # Add metadata to isolated individuals
        for person in chunk_data.get("isolated_individuals", []):
            person['chunk_id'] = chunk_index
            person['extraction_method'] = 'llm'
            # Add genealogical context
            if gen_context.get('generation_number'):
                person['generation_number'] = gen_context['generation_number']
            if gen_context.get('birth_years'):
                person['context_birth_years'] = [by['year'] for by in gen_context['birth_years']]

        return chunk_data

    def _save_to_database(self) -> dict:
        """Save extracted data to database"""
        try:
            repository = GenealogyDataRepository()
            return repository.save_extraction_data(self.all_families, self.all_isolated_individuals)
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            raise


    def run(self):
        """Run the complete extraction workflow"""
        # Initialize
        self.update_progress('initializing', 0)

        self.extractor = self._create_extractor()
        self._load_and_split_text()

        self.update_progress(
            'processing', 5,
            total_chunks=len(self.chunks),
            current_chunk=0
        )

        # Get active prompt once
        active_prompt = self._get_active_prompt()

        # Process chunks
        for i, chunk in enumerate(self.chunks):
            current_chunk = i + 1
            progress = int((i / len(self.chunks)) * 85) + 5  # 5-90% for processing

            logger.info(f"Processing chunk {current_chunk}/{len(self.chunks)}")

            self.update_progress(
                'processing', progress,
                total_chunks=len(self.chunks),
                current_chunk=current_chunk
            )

            chunk_data = self._process_chunk(i, chunk, active_prompt)
            self.all_families.extend(chunk_data.get("families", []))
            self.all_isolated_individuals.extend(chunk_data.get("isolated_individuals", []))

        # Save to database
        self.update_progress(
            'saving', 95,
            total_chunks=len(self.chunks),
            current_chunk=len(self.chunks)
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


@celery.task(bind=True, autoretry_for=BaseFileProcessingTask.autoretry_for, 
             retry_kwargs=BaseFileProcessingTask.retry_kwargs)
def extract_genealogy_data(self, text_file: str = None):
    """
    Extract genealogy data from text using LLM

    Args:
        text_file: Path to text file (optional, defaults to consolidated_text.txt)

    Returns:
        dict: Extraction results with summary statistics
    """
    task_handler = BaseFileProcessingTask()
    task_manager = ExtractionTaskManager(self.request.id, text_file)
    
    return task_handler.execute_with_error_handling(task_manager.run)
