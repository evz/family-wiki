"""
Repository for GEDCOM-related database operations
"""

from web_app.database import db
from web_app.database.models import Family, Occupation, Person, Place


class GedcomRepository:
    """Repository for managing GEDCOM data in the database"""

    def __init__(self, db_session=None):
        self.db_session = db_session or db.session
        self.place_cache: dict[str, Place] = {}

    def create_person(self, person_data: dict) -> Person:
        """Create a person from parsed GEDCOM data"""
        person = Person(
            gedcom_id=person_data.get('gedcom_id'),
            given_names=person_data.get('given_names', ''),
            surname=person_data.get('surname', ''),
            tussenvoegsel=person_data.get('tussenvoegsel', ''),
            sex=person_data.get('sex', ''),
            birth_date=person_data.get('birth_date', ''),
            baptism_date=person_data.get('baptism_date', ''),
            death_date=person_data.get('death_date', ''),
            notes=person_data.get('notes', '').strip()
        )

        # Handle places
        if person_data.get('birth_place'):
            person.birth_place_id = self.get_or_create_place(person_data['birth_place'])
        if person_data.get('baptism_place'):
            person.baptism_place_id = self.get_or_create_place(person_data['baptism_place'])
        if person_data.get('death_place'):
            person.death_place_id = self.get_or_create_place(person_data['death_place'])

        self.db_session.add(person)

        # Handle occupations
        for occupation_title in person_data.get('occupations', []):
            if occupation_title.strip():
                occupation = Occupation(person=person, title=occupation_title)
                self.db_session.add(occupation)

        return person

    def create_family(self, family_data: dict) -> Family:
        """Create a family from parsed GEDCOM data"""
        family = Family(
            family_identifier=family_data.get('gedcom_id'),
            marriage_date=family_data.get('marriage_date', '')
        )

        # Handle marriage place
        if family_data.get('marriage_place'):
            family.marriage_place_id = self.get_or_create_place(family_data['marriage_place'])

        self.db_session.add(family)
        return family

    def establish_family_relationships(self, family: Family, family_data: dict, person_lookup: dict[str, Person]):
        """Establish relationships between family members"""
        # Set father
        if family_data.get('husband_gedcom_id'):
            father = person_lookup.get(family_data['husband_gedcom_id'])
            if father:
                family.father = father

        # Set mother
        if family_data.get('wife_gedcom_id'):
            mother = person_lookup.get(family_data['wife_gedcom_id'])
            if mother:
                family.mother = mother

        # Add children
        for child_gedcom_id in family_data.get('children_gedcom_ids', []):
            child = person_lookup.get(child_gedcom_id)
            if child:
                family.children.append(child)

    def get_or_create_place(self, place_name: str) -> str | None:
        """Get or create a Place object, return its ID"""
        if not place_name or not place_name.strip():
            return None

        place_name = place_name.strip()

        # Check cache first
        if place_name in self.place_cache:
            return self.place_cache[place_name].id

        # Check if place exists in database
        existing_place = self.db_session.query(Place).filter_by(name=place_name).first()
        if existing_place:
            self.place_cache[place_name] = existing_place
            return existing_place.id

        # Create new place
        new_place = Place(name=place_name)
        self.db_session.add(new_place)
        self.db_session.flush()  # Get the ID without committing
        self.place_cache[place_name] = new_place
        return new_place.id

    def commit(self):
        """Commit all changes to database"""
        self.db_session.commit()

    def rollback(self):
        """Rollback all changes"""
        self.db_session.rollback()
