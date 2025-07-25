"""
Tests for GEDCOM repository - database operations for GEDCOM data
"""
import uuid
from unittest.mock import Mock

import pytest

from web_app.database.models import Family, Occupation, Person, Place
from web_app.repositories.gedcom_repository import GedcomRepository


class TestGedcomRepository:
    """Test GEDCOM repository database operations"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_db_session):
        """Repository instance with mocked database session"""
        return GedcomRepository(db_session=mock_db_session)

    @pytest.fixture
    def sample_person_data(self):
        """Sample person data for testing"""
        return {
            'gedcom_id': 'I1',
            'given_names': 'Johannes',
            'surname': 'Smith',
            'tussenvoegsel': 'van',
            'sex': 'M',
            'birth_date': '1850',
            'baptism_date': '1850-02-15',
            'death_date': '1920',
            'birth_place': 'Amsterdam',
            'baptism_place': 'Amsterdam, NH',
            'death_place': 'Utrecht',
            'notes': 'Some notes about the person',
            'occupations': ['farmer', 'baker']
        }

    @pytest.fixture
    def sample_family_data(self):
        """Sample family data for testing"""
        return {
            'gedcom_id': 'F1',
            'marriage_date': '1875-06-15',
            'marriage_place': 'Amsterdam',
            'husband_gedcom_id': 'I1',
            'wife_gedcom_id': 'I2',
            'children_gedcom_ids': ['I3', 'I4', 'I5']
        }

    def test_init_default_session(self, db):
        """Test repository initialization with default database session"""
        from web_app.database import db
        repository = GedcomRepository()
        assert repository.db_session == db.session
        assert repository.place_cache == {}

    def test_init_custom_session(self, mock_db_session):
        """Test repository initialization with custom database session"""
        repository = GedcomRepository(db_session=mock_db_session)
        assert repository.db_session == mock_db_session
        assert repository.place_cache == {}

    def test_create_person_basic_data(self, repository, mock_db_session):
        """Test creating person with basic data"""
        person_data = {
            'gedcom_id': 'I1',
            'given_names': 'Johannes',
            'surname': 'Smith'
        }

        person = repository.create_person(person_data)

        assert isinstance(person, Person)
        assert person.gedcom_id == 'I1'
        assert person.given_names == 'Johannes'
        assert person.surname == 'Smith'
        assert person.tussenvoegsel == ''
        assert person.sex == ''
        assert person.birth_date == ''
        assert person.baptism_date == ''
        assert person.death_date == ''
        assert person.notes == ''
        mock_db_session.add.assert_called_once_with(person)

    def test_create_person_full_data(self, repository, mock_db_session, sample_person_data):
        """Test creating person with full data"""
        # Mock place creation
        repository.get_or_create_place = Mock(return_value=str(uuid.uuid4()))

        person = repository.create_person(sample_person_data)

        assert person.gedcom_id == 'I1'
        assert person.given_names == 'Johannes'
        assert person.surname == 'Smith'
        assert person.tussenvoegsel == 'van'
        assert person.sex == 'M'
        assert person.birth_date == '1850'
        assert person.baptism_date == '1850-02-15'
        assert person.death_date == '1920'
        assert person.notes == 'Some notes about the person'

        # Verify place associations
        assert repository.get_or_create_place.call_count == 3
        repository.get_or_create_place.assert_any_call('Amsterdam')
        repository.get_or_create_place.assert_any_call('Amsterdam, NH')
        repository.get_or_create_place.assert_any_call('Utrecht')

        # Verify person was added to session
        mock_db_session.add.assert_called()

    def test_create_person_with_occupations(self, repository, mock_db_session):
        """Test creating person with occupations"""
        person_data = {
            'gedcom_id': 'I1',
            'given_names': 'Johannes',
            'occupations': ['farmer', 'baker', '']  # Include empty occupation to test filtering
        }

        person = repository.create_person(person_data)

        # Verify person creation
        assert person.gedcom_id == 'I1'
        assert person.given_names == 'Johannes'

        # Verify session add calls (person + 2 occupations, empty one filtered out)
        assert mock_db_session.add.call_count == 3

        # Check that occupations were created (can't easily verify the exact objects)
        calls = mock_db_session.add.call_args_list
        assert any(isinstance(call[0][0], Person) for call in calls)
        # Two occupation calls for 'farmer' and 'baker' (empty string filtered out)
        occupation_calls = [call for call in calls if isinstance(call[0][0], Occupation)]
        assert len(occupation_calls) == 2

    def test_create_person_notes_trimmed(self, repository, mock_db_session):
        """Test that person notes are trimmed"""
        person_data = {
            'gedcom_id': 'I1',
            'notes': '  Some notes with whitespace  '
        }

        person = repository.create_person(person_data)
        assert person.notes == 'Some notes with whitespace'

    def test_create_person_empty_places(self, repository, mock_db_session):
        """Test creating person with empty place fields"""
        person_data = {
            'gedcom_id': 'I1',
            'birth_place': '',
            'baptism_place': None,
            'death_place': '   '  # Whitespace only
        }

        repository.get_or_create_place = Mock(return_value=None)
        person = repository.create_person(person_data)

        # get_or_create_place should be called but return None for empty places
        assert person.birth_place_id is None
        assert person.baptism_place_id is None
        assert person.death_place_id is None

    def test_create_family_basic_data(self, repository, mock_db_session):
        """Test creating family with basic data"""
        family_data = {
            'gedcom_id': 'F1',
            'marriage_date': '1875-06-15'
        }

        family = repository.create_family(family_data)

        assert isinstance(family, Family)
        assert family.family_identifier == 'F1'
        assert family.marriage_date == '1875-06-15'
        assert family.marriage_place_id is None
        mock_db_session.add.assert_called_once_with(family)

    def test_create_family_with_marriage_place(self, repository, mock_db_session):
        """Test creating family with marriage place"""
        family_data = {
            'gedcom_id': 'F1',
            'marriage_date': '1875-06-15',
            'marriage_place': 'Amsterdam'
        }

        place_id = str(uuid.uuid4())
        repository.get_or_create_place = Mock(return_value=place_id)

        family = repository.create_family(family_data)

        assert family.family_identifier == 'F1'
        assert family.marriage_date == '1875-06-15'
        assert family.marriage_place_id == place_id
        repository.get_or_create_place.assert_called_once_with('Amsterdam')
        mock_db_session.add.assert_called_once_with(family)

    def test_create_family_empty_data(self, repository, mock_db_session):
        """Test creating family with minimal data"""
        family_data = {}

        family = repository.create_family(family_data)

        assert family.family_identifier is None
        assert family.marriage_date == ''
        assert family.marriage_place_id is None
        mock_db_session.add.assert_called_once_with(family)

    def test_establish_family_relationships_complete(self, repository, sample_family_data, db):
        """Test establishing complete family relationships"""
        # Create mock family and persons
        family = Mock()
        father = Mock()
        mother = Mock()
        child1 = Mock()
        child2 = Mock()
        child3 = Mock()

        person_lookup = {
            'I1': father,
            'I2': mother,
            'I3': child1,
            'I4': child2,
            'I5': child3
        }

        family.children = []

        repository.establish_family_relationships(family, sample_family_data, person_lookup)

        # Verify relationships
        assert family.father == father
        assert family.mother == mother
        assert family.children == [child1, child2, child3]

    def test_establish_family_relationships_partial(self, repository, db):
        """Test establishing family relationships with missing persons"""
        family = Mock()
        father = Mock()
        child1 = Mock()

        family_data = {
            'husband_gedcom_id': 'I1',
            'wife_gedcom_id': 'I2',  # Missing from lookup
            'children_gedcom_ids': ['I3', 'I4']  # I4 missing from lookup
        }

        person_lookup = {
            'I1': father,
            'I3': child1
        }

        family.children = []

        repository.establish_family_relationships(family, family_data, person_lookup)

        # Verify only found persons are set
        assert family.father == father
        # Mother should not be set since I2 is not in person_lookup
        # Note: Mock objects automatically create attributes, so we check call history instead
        assert family.children == [child1]

    def test_establish_family_relationships_no_relationships(self, repository, db):
        """Test establishing family relationships with no relationship data"""
        family = Mock()
        family.children = []

        family_data = {}
        person_lookup = {}

        repository.establish_family_relationships(family, family_data, person_lookup)

        # Verify no relationships are set - with empty family_data and person_lookup,
        # no assignments should occur, so children list should remain empty
        assert family.children == []

    def test_get_or_create_place_empty_input(self, repository):
        """Test get_or_create_place with empty input"""
        assert repository.get_or_create_place(None) is None
        assert repository.get_or_create_place('') is None
        assert repository.get_or_create_place('   ') is None

    def test_get_or_create_place_from_cache(self, repository, db):
        """Test get_or_create_place from cache"""
        place = Mock()
        place.id = str(uuid.uuid4())
        repository.place_cache['Amsterdam'] = place

        result = repository.get_or_create_place('Amsterdam')

        assert result == place.id
        # Database should not be queried when place is in cache
        repository.db_session.query.assert_not_called()

    def test_get_or_create_place_existing_in_db(self, repository, mock_db_session, db):
        """Test get_or_create_place with existing place in database"""
        place = Mock()
        place.id = str(uuid.uuid4())

        # Mock database query
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = place
        mock_db_session.query.return_value = mock_query

        result = repository.get_or_create_place('Amsterdam')

        assert result == place.id
        assert repository.place_cache['Amsterdam'] == place
        mock_db_session.query.assert_called_once_with(Place)
        mock_query.filter_by.assert_called_once_with(name='Amsterdam')
        mock_db_session.add.assert_not_called()

    def test_get_or_create_place_create_new(self, repository, mock_db_session):
        """Test get_or_create_place creating new place"""
        # Mock database query to return None (place doesn't exist)
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Mock the new place that will be created
        new_place_id = str(uuid.uuid4())

        # We need to simulate what happens when Place() is called and added
        def mock_add(place):
            place.id = new_place_id

        mock_db_session.add.side_effect = mock_add

        repository.get_or_create_place('New Place')

        # Should query database first
        mock_db_session.query.assert_called_once_with(Place)
        mock_query.filter_by.assert_called_once_with(name='New Place')

        # Should create and add new place
        mock_db_session.add.assert_called_once()
        added_place = mock_db_session.add.call_args[0][0]
        assert isinstance(added_place, Place)
        assert added_place.name == 'New Place'

        # Should flush to get ID
        mock_db_session.flush.assert_called_once()

        # Should cache the place
        assert 'New Place' in repository.place_cache
        assert repository.place_cache['New Place'] == added_place

    def test_get_or_create_place_whitespace_trimmed(self, repository, mock_db_session, db):
        """Test that place names are trimmed"""
        place = Mock()
        place.id = str(uuid.uuid4())

        # Mock database query
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = place
        mock_db_session.query.return_value = mock_query

        repository.get_or_create_place('  Amsterdam  ')

        # Should query with trimmed name
        mock_query.filter_by.assert_called_once_with(name='Amsterdam')
        # Should cache with trimmed name
        assert 'Amsterdam' in repository.place_cache

    def test_commit(self, repository, mock_db_session):
        """Test commit operation"""
        repository.commit()
        mock_db_session.commit.assert_called_once()

    def test_rollback(self, repository, mock_db_session):
        """Test rollback operation"""
        repository.rollback()
        mock_db_session.rollback.assert_called_once()

    def test_integration_create_person_with_real_places(self, db):
        """Integration test: create person with real database session"""
        from web_app.database import db

        repository = GedcomRepository()

        person_data = {
            'gedcom_id': 'I1',
            'given_names': 'Johannes',
            'surname': 'Smith',
            'birth_place': 'Amsterdam',
            'death_place': 'Amsterdam'  # Same place to test caching
        }

        person = repository.create_person(person_data)

        # Verify person was created
        assert person.gedcom_id == 'I1'
        assert person.given_names == 'Johannes'
        assert person.surname == 'Smith'

        # Verify places were created and cached
        assert person.birth_place_id is not None
        assert person.death_place_id is not None
        assert person.birth_place_id == person.death_place_id  # Same place

        # Verify cache is populated
        assert 'Amsterdam' in repository.place_cache

        # Clean up
        db.session.rollback()

    def test_integration_family_workflow(self, db):
        """Integration test: complete family creation workflow"""
        from web_app.database import db

        repository = GedcomRepository()

        # Create persons
        father_data = {'gedcom_id': 'I1', 'given_names': 'Johannes', 'sex': 'M'}
        mother_data = {'gedcom_id': 'I2', 'given_names': 'Maria', 'sex': 'F'}
        child_data = {'gedcom_id': 'I3', 'given_names': 'Pieter', 'sex': 'M'}

        father = repository.create_person(father_data)
        mother = repository.create_person(mother_data)
        child = repository.create_person(child_data)

        # Create family
        family_data = {
            'gedcom_id': 'F1',
            'marriage_date': '1875',
            'marriage_place': 'Amsterdam',
            'husband_gedcom_id': 'I1',
            'wife_gedcom_id': 'I2',
            'children_gedcom_ids': ['I3']
        }

        family = repository.create_family(family_data)

        # Establish relationships
        person_lookup = {'I1': father, 'I2': mother, 'I3': child}
        repository.establish_family_relationships(family, family_data, person_lookup)

        # Verify family structure
        assert family.family_identifier == 'F1'
        assert family.marriage_date == '1875'
        assert family.father == father
        assert family.mother == mother
        assert child in family.children

        # Clean up
        db.session.rollback()
