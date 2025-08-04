"""
Repository for GEDCOM-related database operations
"""

from web_app.database.models import Family, Occupation, Person
from web_app.repositories.genealogy_base_repository import GenealogyBaseRepository


class GedcomRepository(GenealogyBaseRepository):
    """Repository for managing GEDCOM data in the database"""

    def __init__(self, db_session=None):
        super().__init__(db_session)

    def create_person(self, person_data: dict) -> Person:
        """Create a person from parsed GEDCOM data"""
        def _create_person():
            # Use base class to create person with common fields
            person = self.create_basic_person(person_data)

            # Add GEDCOM-specific fields
            person.gedcom_id = person_data.get('gedcom_id')
            person.sex = person_data.get('sex', '')

            self.db_session.add(person)

            # Handle occupations (GEDCOM-specific)
            for occupation_title in person_data.get('occupations', []):
                if occupation_title.strip():
                    occupation = Occupation(person=person, title=occupation_title)
                    self.db_session.add(occupation)

            return person

        return self.safe_operation(_create_person, f"create person {person_data.get('gedcom_id', 'unknown')}")

    def create_family(self, family_data: dict) -> Family:
        """Create a family from parsed GEDCOM data"""
        def _create_family():
            # Use base class to create family with common fields
            family = self.create_basic_family(family_data)

            # Add GEDCOM-specific fields
            family.family_identifier = family_data.get('gedcom_id')

            self.db_session.add(family)
            return family

        return self.safe_operation(_create_family, f"create family {family_data.get('gedcom_id', 'unknown')}")

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


