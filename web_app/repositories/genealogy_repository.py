"""
Repository for genealogy data operations - separated from business logic
"""


from web_app.database import db
from web_app.database.models import Event, Family, Marriage, Person, Place
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class GenealogyDataRepository:
    """Repository for genealogy data operations"""

    def clear_all_data(self) -> None:
        """Clear all genealogy data from database"""
        try:
            # Delete in order to respect foreign key constraints
            Family.query.delete()
            Marriage.query.delete()
            Event.query.delete()
            Person.query.delete()
            Place.query.delete()
            db.session.commit()
            logger.info("All genealogy data cleared from database")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing genealogy data: {e}")
            raise

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics"""
        try:
            stats = {
                'total_people': Person.query.count(),
                'total_families': Family.query.count(),
                'total_marriages': Marriage.query.count(),
                'total_events': Event.query.count(),
                'total_places': Place.query.count()
            }
            logger.debug(f"Database stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            raise

    def save_extraction_data(self, families: list[dict], isolated_individuals: list[dict]) -> dict[str, int]:
        """Save extraction data to database"""
        try:
            # Clear existing data first
            self.clear_all_data()

            # Cache for places to avoid duplicates
            place_cache = {}

            # Create families
            family_count = 0
            for family_data in families:
                family = self._create_family_from_data(family_data, place_cache)
                if family:
                    db.session.add(family)
                    family_count += 1

            # Create isolated individuals
            person_count = 0
            for person_data in isolated_individuals:
                person = self._create_person_from_data(person_data, place_cache)
                if person:
                    db.session.add(person)
                    person_count += 1

            # Commit all changes
            db.session.commit()

            result = {
                'families_created': family_count,
                'people_created': person_count,
                'places_created': len(place_cache)
            }

            logger.info(f"Saved extraction data: {result}")
            return result

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving extraction data: {e}")
            raise

    def _create_family_from_data(self, family_data: dict, place_cache: dict) -> Family | None:
        """Create Family object from extracted data"""
        try:
            family = Family()

            # Set basic family info
            family.notes = family_data.get('description', '')
            family.generation_number = self._parse_generation(family_data.get('generation', ''))
            family.family_identifier = family_data.get('group_id', '')

            # Create parents
            if 'parents' in family_data:
                parents = family_data['parents']

                # Create father
                if 'father' in parents:
                    father = self._create_person_from_data(parents['father'], place_cache)
                    if father:
                        db.session.add(father)
                        db.session.flush()  # Get the ID
                        family.father_id = father.id

                # Create mother
                if 'mother' in parents:
                    mother = self._create_person_from_data(parents['mother'], place_cache)
                    if mother:
                        db.session.add(mother)
                        db.session.flush()  # Get the ID
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
                        marriage_place = self._get_or_create_place(marriage_place_name, place_cache)
                        if marriage_place:
                            marriage.marriage_place_id = marriage_place.id
                    
                    db.session.add(marriage)

            # Create children
            if 'children' in family_data:
                for child_data in family_data['children']:
                    child = self._create_person_from_data(child_data, place_cache)
                    if child:
                        db.session.add(child)
                        db.session.flush()  # Get the ID
                        family.children.append(child)

            logger.debug(f"Created family: {family.family_identifier or family.id}")
            return family

        except Exception as e:
            logger.error(f"Error creating family from data: {e}")
            return None

    def _create_person_from_data(self, person_data: dict, place_cache: dict) -> Person | None:
        """Create Person object from extracted data"""
        try:
            person = Person()

            # Parse name components
            given_names, tussenvoegsel, surname = self._parse_dutch_name(person_data)
            person.given_names = given_names
            person.tussenvoegsel = tussenvoegsel
            person.surname = surname

            # Set life events
            person.birth_date = person_data.get('birth_date', '')
            person.baptism_date = person_data.get('baptism_date', '')
            person.death_date = person_data.get('death_date', '')

            # Set additional info
            person.confidence_score = person_data.get('confidence_score', 0.0)
            person.notes = person_data.get('notes', '')

            # Handle places properly - create Place objects and set the IDs
            birth_place_name = person_data.get('birth_place', '')
            if birth_place_name:
                birth_place = self._get_or_create_place(birth_place_name, place_cache)
                if birth_place:
                    person.birth_place_id = birth_place.id

            baptism_place_name = person_data.get('baptism_place', '')
            if baptism_place_name:
                baptism_place = self._get_or_create_place(baptism_place_name, place_cache)
                if baptism_place:
                    person.baptism_place_id = baptism_place.id

            death_place_name = person_data.get('death_place', '')
            if death_place_name:
                death_place = self._get_or_create_place(death_place_name, place_cache)
                if death_place:
                    person.death_place_id = death_place.id

            logger.debug(f"Created person: {person.given_names} {person.surname}")
            return person

        except Exception as e:
            logger.error(f"Error creating person from data: {e}")
            return None

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

    def _get_or_create_place(self, place_name: str, place_cache: dict) -> Place | None:
        """Get or create a place record"""
        if not place_name or not place_name.strip():
            return None

        place_name = place_name.strip()

        # Check cache first
        if place_name in place_cache:
            return place_cache[place_name]

        # Check database
        place = Place.query.filter_by(name=place_name).first()
        if place:
            place_cache[place_name] = place
            return place

        # Create new place
        try:
            place = Place(name=place_name)
            db.session.add(place)
            db.session.flush()  # Get the ID
            place_cache[place_name] = place
            logger.debug(f"Created place: {place_name}")
            return place
        except Exception as e:
            logger.error(f"Error creating place {place_name}: {e}")
            return None

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
