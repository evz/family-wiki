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

    def get_active_prompt(self) -> ExtractionPrompt | None:
        """Get the currently active extraction prompt"""
        return ExtractionPrompt.query.filter_by(is_active=True).first()

    def get_all_prompts(self) -> list[ExtractionPrompt]:
        """Get all prompts ordered by creation date"""
        return ExtractionPrompt.query.order_by(ExtractionPrompt.created_at.desc()).all()

    def get_prompt_by_id(self, prompt_id: str) -> ExtractionPrompt | None:
        """Get a prompt by its ID"""
        try:
            uuid_obj = uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id
            return db.session.get(ExtractionPrompt, uuid_obj)
        except ValueError:
            logger.error(f"Invalid UUID format: {prompt_id}")
            return None

    def create_prompt(self, name: str, prompt_text: str, description: str = "") -> ExtractionPrompt:
        """Create a new extraction prompt"""
        prompt = ExtractionPrompt(
            name=name,
            prompt_text=prompt_text,
            description=description,
            is_active=False
        )
        db.session.add(prompt)
        db.session.commit()
        logger.info(f"Created new prompt: {name}")
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

    def set_active_prompt(self, prompt_id: str) -> bool:
        """Set a prompt as the active one (deactivates all others)"""
        try:
            uuid_obj = uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id

            # Deactivate all prompts
            ExtractionPrompt.query.update({'is_active': False})

            # Activate the specified prompt
            prompt = db.session.get(ExtractionPrompt, uuid_obj)
            if not prompt:
                db.session.rollback()
                return False
        except ValueError:
            logger.error(f"Invalid UUID format: {prompt_id}")
            db.session.rollback()
            return False

        prompt.is_active = True
        db.session.commit()
        logger.info(f"Set active prompt: {prompt.name}")
        return True

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt (cannot delete if it's the only one or if it's active)"""
        try:
            uuid_obj = uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id
            prompt = db.session.get(ExtractionPrompt, uuid_obj)
            if not prompt:
                return False
        except ValueError:
            logger.error(f"Invalid UUID format: {prompt_id}")
            return False

        # Don't allow deleting the active prompt
        if prompt.is_active:
            logger.warning("Cannot delete active prompt")
            return False

        # Don't allow deleting if it's the only prompt
        total_prompts = ExtractionPrompt.query.count()
        if total_prompts <= 1:
            logger.warning("Cannot delete the only remaining prompt")
            return False

        db.session.delete(prompt)
        db.session.commit()
        logger.info(f"Deleted prompt: {prompt.name}")
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
                "description": "Default prompt for extracting Dutch genealogical family data with family-focused approach"
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

                # Check if this prompt already exists (by name)
                existing = ExtractionPrompt.query.filter_by(name=metadata["name"]).first()
                if existing:
                    logger.info(f"Default prompt already exists: {metadata['name']}")
                    continue

                # Create the prompt
                prompt = self.create_prompt(
                    name=metadata["name"],
                    prompt_text=prompt_text,
                    description=metadata["description"]
                )
                created_prompts.append(prompt)
                logger.info(f"Loaded default prompt: {metadata['name']}")

            except Exception as e:
                logger.error(f"Failed to load default prompt from {prompt_file}: {e}")

        # If this is the first prompt, make it active
        if created_prompts and not self.get_active_prompt():
            self.set_active_prompt(str(created_prompts[0].id))
            logger.info(f"Set first default prompt as active: {created_prompts[0].name}")

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
            prompt = ExtractionPrompt.query.filter_by(name=prompt_name).first()
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
