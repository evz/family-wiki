"""
Tests for GenealogyDataRepository
"""


import pytest

from app import create_app
from tests.conftest import BaseTestConfig
from web_app.database import db
from web_app.database.models import Family, Person, Place
from web_app.repositories.genealogy_repository import GenealogyDataRepository


@pytest.fixture
def app():
    """Create test app"""
    app = create_app(BaseTestConfig())

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def repository(app):
    """Create repository instance"""
    with app.app_context():
        return GenealogyDataRepository()


class TestGenealogyDataRepository:
    """Test the genealogy data repository"""

    def test_get_database_stats_empty(self, repository):
        """Test getting stats from empty database"""
        stats = repository.get_database_stats()

        assert stats['total_people'] == 0
        assert stats['total_families'] == 0
        assert stats['total_marriages'] == 0
        assert stats['total_events'] == 0
        assert stats['total_places'] == 0

    def test_get_database_stats_with_data(self, repository, app):
        """Test getting stats with some data"""
        with app.app_context():
            # Add some test data (let IDs auto-generate)
            person = Person(given_names="Jan", surname="Doe")
            family = Family()
            place = Place(name="Amsterdam")

            db.session.add_all([person, family, place])
            db.session.commit()

            stats = repository.get_database_stats()

            assert stats['total_people'] == 1
            assert stats['total_families'] == 1
            assert stats['total_places'] == 1

    def test_clear_all_data(self, repository, app):
        """Test clearing all genealogy data"""
        with app.app_context():
            # Add some test data (let IDs auto-generate)
            person = Person(given_names="Jan", surname="Doe")
            family = Family()
            place = Place(name="Amsterdam")

            db.session.add_all([person, family, place])
            db.session.commit()

            # Verify data exists
            assert Person.query.count() == 1
            assert Family.query.count() == 1
            assert Place.query.count() == 1

            # Clear data
            repository.clear_all_data()

            # Verify data is cleared
            assert Person.query.count() == 0
            assert Family.query.count() == 0
            assert Place.query.count() == 0

    def test_parse_dutch_name_simple(self, repository):
        """Test parsing simple Dutch names"""
        person_data = {
            'given_names': 'Jan Willem',
            'surname': 'Jansen'
        }

        given, tussenvoegsel, surname = repository._parse_dutch_name(person_data)

        assert given == 'Jan Willem'
        assert tussenvoegsel == ''
        assert surname == 'Jansen'

    def test_parse_dutch_name_with_tussenvoegsel(self, repository):
        """Test parsing Dutch names with tussenvoegsel"""
        person_data = {
            'name': 'Jan van der Berg'
        }

        given, tussenvoegsel, surname = repository._parse_dutch_name(person_data)

        assert given == 'Jan'
        assert tussenvoegsel == 'van der'
        assert surname == 'Berg'

    def test_parse_dutch_name_from_components(self, repository):
        """Test parsing when components are provided"""
        person_data = {
            'given_names': 'Maria',
            'tussenvoegsel': 'de',
            'surname': 'Jong'
        }

        given, tussenvoegsel, surname = repository._parse_dutch_name(person_data)

        assert given == 'Maria'
        assert tussenvoegsel == 'de'
        assert surname == 'Jong'

    def test_get_or_create_place_new(self, repository, app):
        """Test creating new place"""
        with app.app_context():
            place_cache = {}
            place = repository._get_or_create_place("Amsterdam", place_cache)

            assert place is not None
            assert place.name == "Amsterdam"
            assert "Amsterdam" in place_cache
            assert Place.query.filter_by(name="Amsterdam").first() is not None

    def test_get_or_create_place_existing(self, repository, app):
        """Test getting existing place"""
        with app.app_context():
            # Create place first
            existing_place = Place(name="Amsterdam")
            db.session.add(existing_place)
            db.session.commit()

            place_cache = {}
            place = repository._get_or_create_place("Amsterdam", place_cache)

            assert place is not None
            assert place.id == existing_place.id
            assert "Amsterdam" in place_cache

    def test_get_or_create_place_cached(self, repository):
        """Test getting place from cache"""
        cached_place = Place(name="Amsterdam")
        place_cache = {"Amsterdam": cached_place}

        place = repository._get_or_create_place("Amsterdam", place_cache)

        assert place is cached_place

    def test_get_or_create_place_empty_name(self, repository):
        """Test handling empty place name"""
        place_cache = {}
        place = repository._get_or_create_place("", place_cache)

        assert place is None

        place = repository._get_or_create_place(None, place_cache)
        assert place is None

    def test_parse_generation_valid(self, repository):
        """Test parsing valid generation strings"""
        assert repository._parse_generation("3") == 3
        assert repository._parse_generation("generation 5") == 5
        assert repository._parse_generation("gen 2") == 2

    def test_parse_generation_invalid(self, repository):
        """Test parsing invalid generation strings"""
        assert repository._parse_generation("") is None
        assert repository._parse_generation(None) is None
        assert repository._parse_generation("no number") is None

    def test_create_person_from_data(self, repository, app):
        """Test creating person from data"""
        with app.app_context():
            person_data = {
                'given_names': 'Jan',
                'surname': 'Doe',
                'birth_date': '1850-01-01',
                'birth_place': 'Amsterdam',
                'notes': 'Test person'
            }

            place_cache = {}
            person = repository._create_person_from_data(person_data, place_cache)

            assert person is not None
            assert person.given_names == 'Jan'
            assert person.surname == 'Doe'
            assert person.birth_date == '1850-01-01'

    def test_save_extraction_data(self, repository, app):
        """Test saving complete extraction data"""
        with app.app_context():
            families = [{
                'description': 'Test Family',
                'parents': {
                    'father': {
                        'given_names': 'John',
                        'surname': 'Doe'
                    },
                    'mother': {
                        'given_names': 'Jane',
                        'surname': 'Smith'
                    }
                },
                'children': [{
                    'given_names': 'Johnny',
                    'surname': 'Doe'
                }]
            }]

            isolated_individuals = [{
                'given_names': 'Bob',
                'surname': 'Jones'
            }]

            result = repository.save_extraction_data(families, isolated_individuals)

            assert result['families_created'] == 1
            assert result['people_created'] == 1

            # Verify data was saved
            assert Family.query.count() == 1
            assert Person.query.count() >= 3  # Father, mother, child + isolated
