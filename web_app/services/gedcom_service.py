"""
GEDCOM service for both CLI and web interface
"""

# Import classes from shared utilities
import json
from collections.abc import Callable
from pathlib import Path

from web_app.shared import DutchDateParser, DutchNameParser, GEDCOMWriter, Person
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class LLMGEDCOMGenerator:
    def __init__(self, llm_data_file: str = "llm_genealogy_results.json"):
        self.llm_data_file = Path(llm_data_file)
        self.gedcom_writer = GEDCOMWriter()

    def load_llm_data(self) -> list:
        """Load LLM-extracted family data and convert to Person objects"""
        if not self.llm_data_file.exists():
            logger.error(f"LLM data file not found: {self.llm_data_file}")
            return []

        with open(self.llm_data_file, encoding='utf-8') as f:
            data = json.load(f)

        people_data = data.get('people', [])
        logger.info(f"Loaded {len(people_data)} people from LLM extraction")

        people = []
        for i, person_data in enumerate(people_data, 1):
            # Parse name components using Dutch utilities
            full_name = f"{person_data.get('given_names', '')} {person_data.get('surname', '')}".strip()
            given_names, tussenvoegsel, surname = DutchNameParser.parse_full_name(full_name)

            # Parse dates using Dutch utilities
            birth_date = DutchDateParser.parse_dutch_date(person_data.get('birth_date', ''))
            baptism_date = DutchDateParser.parse_dutch_date(person_data.get('baptism_date', ''))
            death_date = DutchDateParser.parse_dutch_date(person_data.get('death_date', ''))

            # Create Person object
            person = Person(
                id=f"I{i:04d}",
                given_names=given_names,
                surname=surname,
                tussenvoegsel=tussenvoegsel,
                birth_date=birth_date,
                birth_place=person_data.get('birth_place', ''),
                baptism_date=baptism_date,
                baptism_place=person_data.get('baptism_place', ''),
                death_date=death_date,
                death_place=person_data.get('death_place', ''),
                notes=person_data.get('notes', ''),
                confidence_score=person_data.get('confidence', 0.0)
            )

            people.append(person)

        return people

    def generate_gedcom(self, output_file: str = "family_tree.ged"):
        """Generate GEDCOM file from LLM-extracted data"""
        people = self.load_llm_data()
        if not people:
            logger.warning("No people data found, creating empty GEDCOM file")

        # Add all people to GEDCOM
        for person in people:
            self.gedcom_writer.add_person(person)

        # Generate and save GEDCOM file
        gedcom_content = self.gedcom_writer.generate()
        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(gedcom_content)

        logger.info(f"GEDCOM file saved: {output_path}")
        return {"people": len(people), "output_file": str(output_path)}

class GedcomService:
    """Service for managing GEDCOM generation"""

    def __init__(self):
        self.logger = get_project_logger(__name__)

    def generate_gedcom(self, input_file: str = None, output_file: str = None, progress_callback: Callable = None) -> dict:
        """Generate GEDCOM file from extraction results"""
        try:
            self.logger.info("Starting GEDCOM generation")

            if progress_callback:
                progress_callback({"status": "starting", "message": "Initializing GEDCOM generator"})

            # Use default files if not specified
            input_file = input_file or "pdf_processing/llm_genealogy_results.json"
            output_file = output_file or "family_genealogy.ged"

            generator = LLMGEDCOMGenerator(input_file)

            if progress_callback:
                progress_callback({"status": "running", "message": "Processing family data"})

            # Generate GEDCOM
            results = generator.generate_gedcom(output_file)

            if progress_callback:
                progress_callback({"status": "completed", "results": results})

            self.logger.info("GEDCOM generation completed successfully")

            return {
                "success": True,
                "message": "GEDCOM generation completed",
                "output_file": output_file,
                "results": results
            }

        except Exception as e:
            error_msg = f"GEDCOM generation failed: {str(e)}"
            self.logger.error(error_msg)

            if progress_callback:
                progress_callback({"status": "failed", "error": error_msg})

            return {
                "success": False,
                "error": error_msg
            }

# Global service instance
gedcom_service = GedcomService()
