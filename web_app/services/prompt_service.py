"""
Service for managing LLM extraction prompts
"""

import uuid
from pathlib import Path

from web_app.database import db
from web_app.database.models import ExtractionPrompt
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class PromptService:
    """Service for managing extraction prompts"""

    def get_all_prompts(self, prompt_type: str = None) -> list[ExtractionPrompt]:
        """Get all prompts ordered by creation date, optionally filtered by type"""
        query = db.select(ExtractionPrompt).order_by(ExtractionPrompt.created_at.desc())
        if prompt_type:
            query = query.filter_by(prompt_type=prompt_type)
        return db.session.execute(query).scalars().all()

    def get_prompt_by_id(self, prompt_id: str) -> ExtractionPrompt | None:
        """Get a prompt by its ID"""
        try:
            uuid_obj = uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id
            return db.session.get(ExtractionPrompt, uuid_obj)
        except ValueError:
            logger.error(f"Invalid UUID format: {prompt_id}")
            return None

    def create_prompt(self, name: str, prompt_text: str, prompt_type: str = 'extraction', description: str = "", template_variables: list = None) -> ExtractionPrompt:
        """Create a new prompt"""
        prompt = ExtractionPrompt(
            name=name,
            prompt_text=prompt_text,
            prompt_type=prompt_type,
            description=description,
            template_variables=template_variables or []
        )
        db.session.add(prompt)
        db.session.commit()
        logger.info(f"Created new {prompt_type} prompt: {name}")
        return prompt

    def update_prompt(self, prompt_id: str, name: str = None, prompt_text: str = None,
                     description: str = None) -> ExtractionPrompt | None:
        """Update an existing prompt"""
        try:
            uuid_obj = uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id
            prompt = db.session.get(ExtractionPrompt, uuid_obj)
            if not prompt:
                return None
        except ValueError:
            logger.error(f"Invalid UUID format: {prompt_id}")
            return None

        if name is not None:
            prompt.name = name
        if prompt_text is not None:
            prompt.prompt_text = prompt_text
        if description is not None:
            prompt.description = description

        db.session.commit()
        logger.info(f"Updated prompt: {prompt.name}")
        return prompt


    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt"""
        try:
            uuid_obj = uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id
            prompt = db.session.get(ExtractionPrompt, uuid_obj)
            if not prompt:
                return False
        except ValueError:
            logger.error(f"Invalid UUID format: {prompt_id}")
            return False

        db.session.delete(prompt)
        db.session.commit()
        logger.info(f"Deleted {prompt.prompt_type} prompt: {prompt.name}")
        return True

    def load_default_prompts(self) -> list[ExtractionPrompt]:
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
                existing = db.session.execute(
                    db.select(ExtractionPrompt).filter_by(name=metadata["name"], prompt_type=prompt_type)
                ).scalar_one_or_none()
                if existing:
                    logger.info(f"Default prompt already exists: {metadata['name']}")
                    continue

                # Create the prompt
                prompt = self.create_prompt(
                    name=metadata["name"],
                    prompt_text=prompt_text,
                    prompt_type=prompt_type,
                    description=metadata["description"]
                )
                created_prompts.append(prompt)
                logger.info(f"Loaded default prompt: {metadata['name']}")

            except Exception as e:
                logger.error(f"Failed to load default prompt from {prompt_file}: {e}")

        return created_prompts

    def reset_to_default(self, prompt_name: str = "Default Dutch Genealogy Extraction") -> ExtractionPrompt | None:
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

            # Find existing prompt
            prompt = db.session.execute(
                db.select(ExtractionPrompt).filter_by(name=prompt_name)
            ).scalar_one_or_none()
            if not prompt:
                logger.error(f"Prompt not found: {prompt_name}")
                return None

            # Update with default content
            prompt.prompt_text = default_text
            db.session.commit()
            logger.info(f"Reset prompt to default: {prompt_name}")
            return prompt

        except Exception as e:
            logger.error(f"Failed to reset prompt to default: {e}")
            return None


# Global service instance
prompt_service = PromptService()
