"""
Repository for genealogy data operations - separated from business logic
"""

from web_app.database.models import Family, Marriage, Person
from web_app.repositories.genealogy_base_repository import GenealogyBaseRepository


class GenealogyDataRepository(GenealogyBaseRepository):
    """Repository for genealogy data operations"""

    def clear_all_data(self) -> None:
        """Clear all genealogy data from database"""
        return self.clear_all_genealogy_data()

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics"""
        return super().get_database_stats()

    def save_extraction_data(self, families: list[dict], isolated_individuals: list[dict]) -> dict[str, int]:
        """Save extraction data to database"""
        def _save_extraction_data():
            # Clear existing data first
            self.clear_all_data()

            # Create families
            family_count = 0
            for family_data in families:
                family = self._create_family_from_data(family_data)
                if family:
                    self.db_session.add(family)
                    family_count += 1

            # Create isolated individuals
            person_count = 0
            for person_data in isolated_individuals:
                person = self._create_person_from_data(person_data)
                if person:
                    self.db_session.add(person)
                    person_count += 1

            result = {
                'families_created': family_count,
                'people_created': person_count,
                'places_created': len(self.place_cache)
            }

            self.logger.info(f"Saved extraction data: {result}")
            return result

        return self.safe_operation(_save_extraction_data, "save extraction data")

    def _create_family_from_data(self, family_data: dict) -> Family | None:
        """Create Family object from extracted data"""
        # Use base class to create family with common fields
        family_common_data = {
            'marriage_date': family_data.get('parents', {}).get('marriage_date', ''),
            'marriage_place': family_data.get('parents', {}).get('marriage_place', ''),
            'notes': family_data.get('description', '')
        }
        family = self.create_basic_family(family_common_data)

        # Add extraction-specific fields
        family.generation_number = self._parse_generation(family_data.get('generation', ''))
        family.family_identifier = family_data.get('group_id', '')

        # Create parents
        if 'parents' in family_data:
            parents = family_data['parents']

            # Create father
            if 'father' in parents:
                father = self._create_person_from_data(parents['father'])
                if father:
                    self.db_session.add(father)
                    self.db_session.flush()  # Get the ID
                    family.father_id = father.id

            # Create mother
            if 'mother' in parents:
                mother = self._create_person_from_data(parents['mother'])
                if mother:
                    self.db_session.add(mother)
                    self.db_session.flush()  # Get the ID
                    family.mother_id = mother.id

            # Create marriage record if we have both parents
            if family.father_id and family.mother_id:
                marriage = Marriage(
                    person1_id=family.father_id,
                    person2_id=family.mother_id,
                    marriage_date=parents.get('marriage_date', ''),
                    notes=parents.get('notes', '')
                )

                # Handle marriage place
                marriage_place_name = parents.get('marriage_place', '')
                if marriage_place_name:
                    marriage_place = self.get_or_create_place(marriage_place_name)
                    if marriage_place:
                        marriage.marriage_place_id = marriage_place.id

                self.db_session.add(marriage)

        # Create children
        if 'children' in family_data:
            for child_data in family_data['children']:
                child = self._create_person_from_data(child_data)
                if child:
                    self.db_session.add(child)
                    self.db_session.flush()  # Get the ID
                    family.children.append(child)

        self.logger.debug(f"Created family: {family.family_identifier or family.id}")
        return family

    def _create_person_from_data(self, person_data: dict) -> Person | None:
        """Create Person object from extracted data"""
        # Parse name components first
        given_names, tussenvoegsel, surname = self._parse_dutch_name(person_data)

        # Prepare data for base class
        person_common_data = {
            'given_names': given_names,
            'tussenvoegsel': tussenvoegsel,
            'surname': surname,
            'birth_date': person_data.get('birth_date', ''),
            'baptism_date': person_data.get('baptism_date', ''),
            'death_date': person_data.get('death_date', ''),
            'birth_place': person_data.get('birth_place', ''),
            'baptism_place': person_data.get('baptism_place', ''),
            'death_place': person_data.get('death_place', ''),
            'notes': person_data.get('notes', '')
        }

        # Use base class to create person with common fields
        person = self.create_basic_person(person_common_data)

        # Add extraction-specific fields
        person.confidence_score = person_data.get('confidence_score', 0.0)

        self.logger.debug(f"Created person: {person.given_names} {person.surname}")
        return person

    def _parse_dutch_name(self, person_data: dict) -> tuple[str, str, str]:
        """Parse Dutch name into components"""
        # Basic name parsing logic
        full_name = person_data.get('name', '')
        given_names = person_data.get('given_names', '')
        surname = person_data.get('surname', '')
        tussenvoegsel = person_data.get('tussenvoegsel', '')

        # If we have components, use them
        if given_names or surname:
            return given_names, tussenvoegsel, surname

        # Otherwise, try to parse full name
        if full_name:
            # Simple parsing - can be enhanced with DutchNameParser
            parts = full_name.split()
            if len(parts) >= 2:
                # Last part is surname, first part(s) are given names
                given_names = parts[0]
                surname = parts[-1]
                # Middle parts might be tussenvoegsel
                if len(parts) > 2:
                    tussenvoegsel = ' '.join(parts[1:-1])

        return given_names, tussenvoegsel, surname


    def _parse_generation(self, generation_str: str) -> int | None:
        """Parse generation string to integer"""
        if not generation_str:
            return None

        try:
            # Remove common prefixes/suffixes
            generation_str = generation_str.strip()
            generation_str = generation_str.replace('generation', '').replace('gen', '').strip()

            # Try to convert to int
            return int(generation_str)
        except (ValueError, TypeError):
            return None
