"""
Service for managing LLM extraction prompts
"""

from pathlib import Path

from web_app.database import db
from web_app.repositories.rag_repository import RAGRepository
from web_app.services.exceptions import NotFoundError, handle_service_exceptions
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class PromptService:
    """Service for managing extraction prompts"""

    def __init__(self, db_session=None):
        self.rag_repository = RAGRepository(db_session)
        self.db_session = db_session or db.session

    @handle_service_exceptions(logger)
    def get_all_prompts(self, prompt_type: str = None):
        """Get all prompts ordered by creation date, optionally filtered by type"""
        return self.rag_repository.get_all_prompts(prompt_type)

    @handle_service_exceptions(logger)
    def get_prompt_by_id(self, prompt_id: str):
        """Get a prompt by its ID"""
        try:
            return self.rag_repository.get_prompt_by_id(prompt_id)
        except ValueError as e:
            if "Prompt not found" in str(e):
                raise NotFoundError(str(e)) from e
            else:
                # Re-raise for UUID validation errors
                raise

    @handle_service_exceptions(logger)
    def create_prompt(self, name: str, prompt_text: str, prompt_type: str = 'extraction', description: str = "", template_variables: list = None):
        """Create a new prompt"""
        prompt = self.rag_repository.create_prompt(
            name=name,
            prompt_text=prompt_text,
            prompt_type=prompt_type,
            description=description,
            template_variables=template_variables
        )
        self.db_session.commit()  # In tests this commits to SAVEPOINT, in production commits transaction
        logger.info(f"Created new {prompt_type} prompt: {name}")
        return prompt

    def update_prompt(self, prompt_id: str, name: str = None, prompt_text: str = None, description: str = None):
        """Update an existing prompt"""
        try:
            prompt = self.rag_repository.update_prompt(prompt_id, name, prompt_text, description)
            self.db_session.commit()  # In tests this commits to SAVEPOINT, in production commits transaction
            logger.info(f"Updated prompt: {prompt.name}")
            return prompt
        except ValueError as e:
            if "Prompt not found" in str(e):
                return None  # Test expects None for nonexistent prompts
            elif "badly formed hexadecimal UUID string" in str(e):
                return None  # Test expects None for invalid UUID format
            else:
                # Re-raise other validation errors
                raise

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt"""
        try:
            result = self.rag_repository.delete_prompt(prompt_id)
            self.db_session.commit()  # In tests this commits to SAVEPOINT, in production commits transaction
            logger.info(f"Deleted {result['prompt_type']} prompt: {result['prompt_name']}")
            return True
        except ValueError as e:
            if "Prompt not found" in str(e):
                return False  # Test expects False for nonexistent prompts
            elif "badly formed hexadecimal UUID string" in str(e):
                return False  # Test expects False for invalid UUID format
            else:
                # Re-raise other validation errors
                raise

    @handle_service_exceptions(logger)
    def load_default_prompts(self):
        """Load default prompts from files during database initialization"""
        prompts_dir = Path(__file__).parent.parent / "database" / "default_prompts"
        created_prompts = []

        if not prompts_dir.exists():
            logger.warning(f"Default prompts directory not found: {prompts_dir}")
            return created_prompts

        # Define prompt files and their metadata
        prompt_files = {
            "dutch_genealogy_extraction.txt": {
                "name": "Default Dutch Genealogy Extraction",
                "description": "Default prompt for extracting Dutch genealogical family data with family-focused approach",
                "prompt_type": "extraction"
            },
            "default_rag_prompt.txt": {
                "name": "Default RAG Query",
                "description": "Default prompt for answering questions about genealogical documents using RAG",
                "prompt_type": "rag"
            }
        }

        for filename, metadata in prompt_files.items():
            prompt_file = prompts_dir / filename
            if not prompt_file.exists():
                logger.warning(f"Default prompt file not found: {prompt_file}")
                continue

            try:
                with open(prompt_file, encoding='utf-8') as f:
                    prompt_text = f.read().strip()

                # Check if this prompt already exists (by name and type)
                prompt_type = metadata.get("prompt_type", "extraction")
                existing = self.rag_repository.get_prompt_by_name_and_type(metadata["name"], prompt_type)
                if existing:
                    logger.info(f"Default prompt already exists: {metadata['name']}")
                    continue

                # Create the prompt using repository
                prompt = self.rag_repository.create_prompt(
                    name=metadata["name"],
                    prompt_text=prompt_text,
                    prompt_type=prompt_type,
                    description=metadata["description"],
                    template_variables=[]
                )
                created_prompts.append(prompt)
                logger.info(f"Loaded default prompt: {metadata['name']}")

            except Exception as e:
                logger.error(f"Failed to load default prompt from {prompt_file}: {e}")

        return created_prompts

    @handle_service_exceptions(logger)
    def reset_to_default(self, prompt_name: str = "Default Dutch Genealogy Extraction"):
        """Reset a prompt to its default content from file (useful for recovery)"""
        prompts_dir = Path(__file__).parent.parent / "database" / "default_prompts"

        # Find the prompt file
        prompt_file = prompts_dir / "dutch_genealogy_extraction.txt"
        if not prompt_file.exists():
            logger.error(f"Default prompt file not found: {prompt_file}")
            return None

        try:
            with open(prompt_file, encoding='utf-8') as f:
                default_text = f.read().strip()

            # Find existing prompt by name (check extraction type first, then any type)
            existing_prompt = self.rag_repository.get_prompt_by_name_and_type(prompt_name, "extraction")
            if not existing_prompt:
                # If not found as extraction type, look for any prompt with this name
                all_prompts = self.rag_repository.get_all_prompts()
                existing_prompt = next((p for p in all_prompts if p.name == prompt_name), None)

            if not existing_prompt:
                logger.error(f"Prompt not found: {prompt_name}")
                return None

            # Update with default content using repository
            prompt = self.rag_repository.update_prompt(
                prompt_id=existing_prompt.id,
                prompt_text=default_text
            )
            logger.info(f"Reset prompt to default: {prompt_name}")
            return prompt

        except Exception as e:
            logger.error(f"Failed to reset prompt to default: {e}")
            return None


