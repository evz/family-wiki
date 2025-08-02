"""
Base repository for genealogy operations - shared functionality for all genealogy repositories
"""

from web_app.database.models import Event, Family, Marriage, Person, Place
from web_app.repositories.base_repository import BaseRepository


class GenealogyBaseRepository(BaseRepository):
    """Base repository for genealogy data operations with shared functionality"""

    def __init__(self, db_session=None):
        super().__init__(db_session)
        self.place_cache: dict[str, Place] = {}

    def get_or_create_place(self, place_name: str) -> Place | None:
        """Get or create a Place object, return the Place"""
        if not place_name or not place_name.strip():
            return None

        place_name = place_name.strip()

        # Check cache first
        if place_name in self.place_cache:
            return self.place_cache[place_name]

        def _get_or_create_place():
            # Check if place exists in database
            existing_place = self.db_session.query(Place).filter_by(name=place_name).first()
            if existing_place:
                self.place_cache[place_name] = existing_place
                return existing_place

            # Create new place
            new_place = Place(name=place_name)
            self.db_session.add(new_place)
            # safe_operation will flush after this function returns
            return new_place

        result = self.safe_operation(_get_or_create_place, f"get or create place {place_name}")
        
        # Cache the result and return it
        if result:
            self.place_cache[place_name] = result
        return result

    def clear_all_genealogy_data(self) -> None:
        """Clear all genealogy data from database"""
        def _clear_all_data():
            # Delete in order to respect foreign key constraints
            Family.query.delete()
            Marriage.query.delete()
            Event.query.delete()
            Person.query.delete()
            Place.query.delete()
            # Clear cache as well
            self.place_cache.clear()
            self.logger.info("All genealogy data cleared from database")

        self.safe_operation(_clear_all_data, "clear all genealogy data")

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics"""
        def _get_stats():
            return {
                'total_people': Person.query.count(),
                'total_families': Family.query.count(),
                'total_marriages': Marriage.query.count(),
                'total_events': Event.query.count(),
                'total_places': Place.query.count()
            }

        return self.safe_query(_get_stats, "get database stats")

    def create_basic_person(self, person_data: dict) -> Person:
        """Create a Person with common fields - to be extended by subclasses"""
        person = Person()
        
        # Set common fields that exist in both data formats
        person.given_names = person_data.get('given_names', '')
        person.surname = person_data.get('surname', '')
        person.tussenvoegsel = person_data.get('tussenvoegsel', '')
        person.birth_date = person_data.get('birth_date', '')
        person.baptism_date = person_data.get('baptism_date', '')
        person.death_date = person_data.get('death_date', '')
        person.notes = person_data.get('notes', '').strip()

        # Handle places
        if person_data.get('birth_place'):
            birth_place = self.get_or_create_place(person_data['birth_place'])
            person.birth_place_id = birth_place.id if birth_place else None
        if person_data.get('baptism_place'):
            baptism_place = self.get_or_create_place(person_data['baptism_place'])
            person.baptism_place_id = baptism_place.id if baptism_place else None
        if person_data.get('death_place'):
            death_place = self.get_or_create_place(person_data['death_place'])
            person.death_place_id = death_place.id if death_place else None

        return person

    def create_basic_family(self, family_data: dict) -> Family:
        """Create a Family with common fields - to be extended by subclasses"""
        family = Family()
        
        # Set common fields
        family.marriage_date = family_data.get('marriage_date', '')
        family.notes = family_data.get('notes', '')

        # Handle marriage place
        if family_data.get('marriage_place'):
            marriage_place = self.get_or_create_place(family_data['marriage_place'])
            family.marriage_place_id = marriage_place.id if marriage_place else None

        return family