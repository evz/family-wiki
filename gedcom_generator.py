#!/usr/bin/env python3
"""
GEDCOM generator for LLM-extracted genealogy data
"""

import json
from pathlib import Path
from typing import List
import logging

from shared_genealogy import Person, GEDCOMWriter, DutchNameParser, DutchDateParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMGEDCOMGenerator:
    def __init__(self, llm_data_file: str = "llm_genealogy_results.json"):
        self.llm_data_file = Path(llm_data_file)
        self.gedcom_writer = GEDCOMWriter()
        
    def load_llm_data(self) -> List[Person]:
        """Load LLM-extracted family data and convert to Person objects"""
        if not self.llm_data_file.exists():
            logger.error(f"LLM data file not found: {self.llm_data_file}")
            return []
        
        with open(self.llm_data_file, 'r', encoding='utf-8') as f:
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
            marriage_date = DutchDateParser.parse_dutch_date(person_data.get('marriage_date', ''))
            
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
            
            # Add marriage information as notes if present
            if marriage_date or person_data.get('marriage_place') or person_data.get('spouse_name'):
                marriage_info = []
                if person_data.get('spouse_name'):
                    marriage_info.append(f"Spouse: {person_data['spouse_name']}")
                if marriage_date:
                    marriage_info.append(f"Marriage: {marriage_date}")
                if person_data.get('marriage_place'):
                    marriage_info.append(f"Marriage place: {person_data['marriage_place']}")
                
                if marriage_info:
                    if person.notes:
                        person.notes += " | " + " | ".join(marriage_info)
                    else:
                        person.notes = " | ".join(marriage_info)
            
            people.append(person)
        
        return people
    
    def generate_gedcom(self, output_file: str = "family_tree.ged") -> None:
        """Generate complete GEDCOM file from LLM data"""
        logger.info("Generating GEDCOM file from LLM extraction results...")
        
        people = self.load_llm_data()
        
        if not people:
            logger.error("No LLM data loaded")
            return
        
        # Use the shared GEDCOMWriter to create the file
        self.gedcom_writer.write_gedcom(people, output_file=output_file)
        
        logger.info(f"GEDCOM file generated: {output_file}")
        logger.info(f"Total individuals: {len(people)}")
        
        # Validation summary
        high_confidence = sum(1 for p in people if p.confidence_score > 0.8)
        logger.info(f"High confidence entries (>0.8): {high_confidence}/{len(people)}")
        
        # Validate the generated GEDCOM
        validation_result = self.gedcom_writer.validate_gedcom(output_file)
        if validation_result['valid']:
            logger.info("GEDCOM validation: PASSED")
        else:
            logger.warning(f"GEDCOM validation issues found: {len(validation_result['issues'])}")
            for issue in validation_result['issues'][:5]:  # Show first 5 issues
                logger.warning(f"  - {issue}")
    
    def print_preview(self, output_file: str = "family_tree.ged", lines: int = 50) -> None:
        """Print a preview of the GEDCOM content"""
        if not Path(output_file).exists():
            print("GEDCOM file not found. Generate it first.")
            return
            
        print(f"\nGEDCOM Preview (first {lines} lines):")
        print("-" * 50)
        
        with open(output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if i > lines:
                    break
                print(line.rstrip())
        
        print(f"... (showing first {lines} lines)")

def main():
    generator = LLMGEDCOMGenerator()
    generator.generate_gedcom()
    generator.print_preview()
    
    print(f"\n✅ GEDCOM file created successfully!")
    print(f"📁 File: family_tree.ged")
    print(f"📊 Import into genealogy software:")
    print(f"   - Gramps (free, open source)")
    print(f"   - Family Tree Maker")
    print(f"   - MyHeritage")
    print(f"   - Ancestry.com")
    print(f"   - FamilySearch")

if __name__ == "__main__":
    main()