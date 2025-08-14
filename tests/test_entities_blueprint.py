"""
Tests for entities blueprint
"""

from unittest.mock import Mock, patch

import pytest

from tests.conftest import BaseTestConfig
from web_app import create_app


class EntitiesBlueprintTestConfig(BaseTestConfig):
    """Test configuration"""
    def __init__(self):
        super().__init__()
        self.sqlalchemy_database_uri = 'sqlite:///:memory:'


class TestEntitiesBlueprint:
    """Test entities blueprint routes"""


    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_genealogy_repository(self):
        """Mock genealogy repository"""
        with patch('web_app.blueprints.entities.GenealogyDataRepository') as mock_repo:
            yield mock_repo

    @pytest.fixture
    def mock_models(self):
        """Mock all database models"""
        mocks = {}
        model_names = ['Person', 'Family', 'Place', 'Event', 'Marriage']

        for model_name in model_names:
            with patch(f'web_app.blueprints.entities.{model_name}') as mock_model:
                mocks[model_name] = mock_model

        return mocks

    def test_index_route_with_stats(self, client, mock_genealogy_repository):
        """Test entities index route with database stats"""
        mock_stats = {
            'persons': 10,
            'families': 5,
            'places': 8,
            'events': 3,
            'marriages': 4,
            'total_entities': 30
        }

        # Configure mock instance
        mock_repo_instance = mock_genealogy_repository.return_value
        mock_repo_instance.get_database_stats.return_value = mock_stats

        response = client.get('/entities/')

        assert response.status_code == 200
        assert b'Database Entities' in response.data
        assert b'10' in response.data  # persons count
        mock_repo_instance.get_database_stats.assert_called_once()

    def test_index_route_no_stats(self, client, mock_genealogy_repository):
        """Test entities index route with no stats"""
        mock_repo_instance = mock_genealogy_repository.return_value
        mock_repo_instance.get_database_stats.return_value = {}

        response = client.get('/entities/')

        assert response.status_code == 200
        assert b'No database statistics available' in response.data

    @patch('web_app.blueprints.entities.Person')
    def test_persons_list_route_with_data(self, mock_person, client):
        """Test persons list route with person data"""
        # Mock person objects
        mock_person1 = Mock()
        mock_person1.id = 1
        mock_person1.given_names = "Johannes"
        mock_person1.tussenvoegsel = "van"
        mock_person1.surname = "Berg"
        mock_person1.birth_date = "1850-03-15"
        mock_person1.death_date = "1920-12-03"

        mock_person2 = Mock()
        mock_person2.id = 2
        mock_person2.given_names = "Maria"
        mock_person2.tussenvoegsel = ""
        mock_person2.surname = "de Jong"
        mock_person2.birth_date = "1855-07-02"
        mock_person2.death_date = ""

        # Configure mock query
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_person1, mock_person2]
        mock_person.query = mock_query

        response = client.get('/entities/persons')

        assert response.status_code == 200
        assert b'Johannes' in response.data
        assert b'Maria' in response.data
        mock_query.order_by.assert_called_once()

    @patch('web_app.blueprints.entities.Person')
    def test_persons_list_route_empty(self, mock_person, client):
        """Test persons list route with no data"""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = []
        mock_person.query = mock_query

        response = client.get('/entities/persons')

        assert response.status_code == 200
        assert b'No persons found' in response.data

    @patch('web_app.blueprints.entities.Person')
    def test_person_detail_route_exists(self, mock_person, client):
        """Test person detail route for existing person"""
        mock_person_obj = Mock()
        mock_person_obj.id = 1
        mock_person_obj.given_names = "Johannes"
        mock_person_obj.tussenvoegsel = "van"
        mock_person_obj.surname = "Berg"
        mock_person_obj.birth_date = "1850-03-15"
        mock_person_obj.baptism_date = "1850-03-20"
        mock_person_obj.death_date = "1920-12-03"
        mock_person_obj.notes = "Baker by profession"

        mock_person.query.get_or_404.return_value = mock_person_obj

        response = client.get('/entities/persons/1')

        assert response.status_code == 200
        assert b'Johannes' in response.data
        assert b'Berg' in response.data
        assert b'Baker by profession' in response.data
        mock_person.query.get_or_404.assert_called_once_with('1')

    @patch('web_app.blueprints.entities.Person')
    def test_person_detail_route_not_found(self, mock_person, client):
        """Test person detail route for non-existent person"""
        from werkzeug.exceptions import NotFound

        mock_person.query.get_or_404.side_effect = NotFound()

        response = client.get('/entities/persons/999')

        assert response.status_code == 404

    @patch('web_app.blueprints.entities.Family')
    def test_families_list_route(self, mock_family, client):
        """Test families list route"""
        mock_family1 = Mock()
        mock_family1.id = 1
        mock_family1.family_identifier = "FAM001"
        mock_family1.generation_number = 1
        mock_family1.father = Mock()
        mock_family1.father.given_names = "John"
        mock_family1.father.surname = "Doe"
        mock_family1.mother = Mock()
        mock_family1.mother.given_names = "Jane"
        mock_family1.mother.surname = "Smith"

        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_family1]
        mock_family.query = mock_query

        response = client.get('/entities/families')

        assert response.status_code == 200
        assert b'FAM001' in response.data
        assert b'John' in response.data
        assert b'Jane' in response.data

    @patch('web_app.blueprints.entities.Family')
    def test_family_detail_route(self, mock_family, client):
        """Test family detail route"""
        mock_family_obj = Mock()
        mock_family_obj.id = 1
        mock_family_obj.family_identifier = "FAM001"
        mock_family_obj.generation_number = 1
        mock_family_obj.father = Mock()
        mock_family_obj.father.id = 1
        mock_family_obj.father.given_names = "John"
        mock_family_obj.father.surname = "Doe"
        mock_family_obj.mother = None
        mock_family_obj.children = []
        mock_family_obj.notes = ""

        mock_family.query.get_or_404.return_value = mock_family_obj

        response = client.get('/entities/families/1')

        assert response.status_code == 200
        assert b'FAM001' in response.data
        assert b'John' in response.data

    @patch('web_app.blueprints.entities.Place')
    def test_places_list_route(self, mock_place, client):
        """Test places list route"""
        mock_place1 = Mock()
        mock_place1.id = 1
        mock_place1.name = "Amsterdam"
        mock_place1.country = "Netherlands"

        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_place1]
        mock_place.query = mock_query

        response = client.get('/entities/places')

        assert response.status_code == 200
        assert b'Amsterdam' in response.data
        assert b'Netherlands' in response.data

    @patch('web_app.blueprints.entities.Place')
    def test_place_detail_route(self, mock_place, client):
        """Test place detail route"""
        mock_place_obj = Mock()
        mock_place_obj.id = 1
        mock_place_obj.name = "Amsterdam"
        mock_place_obj.country = "Netherlands"
        mock_place_obj.region = "North Holland"
        mock_place_obj.notes = "Capital city"

        mock_place.query.get_or_404.return_value = mock_place_obj

        response = client.get('/entities/places/1')

        assert response.status_code == 200
        assert b'Amsterdam' in response.data
        assert b'Netherlands' in response.data
        assert b'Capital city' in response.data

    @patch('web_app.blueprints.entities.Event')
    def test_events_list_route(self, mock_event, client):
        """Test events list route"""
        mock_event1 = Mock()
        mock_event1.id = 1
        mock_event1.title = "Birth of Johannes"
        mock_event1.date = "1850-03-15"
        mock_event1.event_type = "Birth"

        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_event1]
        mock_event.query = mock_query

        response = client.get('/entities/events')

        assert response.status_code == 200
        assert b'Birth of Johannes' in response.data
        assert b'Birth' in response.data

    @patch('web_app.blueprints.entities.Event')
    def test_event_detail_route(self, mock_event, client):
        """Test event detail route"""
        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event_obj.title = "Birth of Johannes"
        mock_event_obj.date = "1850-03-15"
        mock_event_obj.event_type = "Birth"
        mock_event_obj.place = Mock()
        mock_event_obj.place.id = 1
        mock_event_obj.place.name = "Amsterdam"
        mock_event_obj.description = "Born at home"

        mock_event.query.get_or_404.return_value = mock_event_obj

        response = client.get('/entities/events/1')

        assert response.status_code == 200
        assert b'Birth of Johannes' in response.data
        assert b'Amsterdam' in response.data
        assert b'Born at home' in response.data

    @patch('web_app.blueprints.entities.Marriage')
    def test_marriages_list_route(self, mock_marriage, client):
        """Test marriages list route"""
        mock_marriage1 = Mock()
        mock_marriage1.id = 1
        mock_marriage1.spouse1 = Mock()
        mock_marriage1.spouse1.given_names = "John"
        mock_marriage1.spouse1.surname = "Doe"
        mock_marriage1.spouse2 = Mock()
        mock_marriage1.spouse2.given_names = "Jane"
        mock_marriage1.spouse2.surname = "Smith"
        mock_marriage1.marriage_date = "1875-06-01"

        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_marriage1]
        mock_marriage.query = mock_query

        response = client.get('/entities/marriages')

        assert response.status_code == 200
        assert b'John' in response.data
        assert b'Jane' in response.data
        assert b'1875-06-01' in response.data

    @patch('web_app.blueprints.entities.Marriage')
    def test_marriage_detail_route(self, mock_marriage, client):
        """Test marriage detail route"""
        mock_marriage_obj = Mock()
        mock_marriage_obj.id = 1
        mock_marriage_obj.spouse1 = Mock()
        mock_marriage_obj.spouse1.id = 1
        mock_marriage_obj.spouse1.given_names = "John"
        mock_marriage_obj.spouse1.surname = "Doe"
        mock_marriage_obj.spouse2 = Mock()
        mock_marriage_obj.spouse2.id = 2
        mock_marriage_obj.spouse2.given_names = "Jane"
        mock_marriage_obj.spouse2.surname = "Smith"
        mock_marriage_obj.marriage_date = "1875-06-01"
        mock_marriage_obj.marriage_place = Mock()
        mock_marriage_obj.marriage_place.id = 1
        mock_marriage_obj.marriage_place.name = "Amsterdam"
        mock_marriage_obj.notes = "Church wedding"

        mock_marriage.query.get_or_404.return_value = mock_marriage_obj

        response = client.get('/entities/marriages/1')

        assert response.status_code == 200
        assert b'John' in response.data
        assert b'Jane' in response.data
        assert b'Church wedding' in response.data

    def test_error_handling_index(self, client, mock_genealogy_repository):
        """Test error handling on index route"""
        mock_repo_instance = mock_genealogy_repository.return_value
        mock_repo_instance.get_database_stats.side_effect = Exception("Database error")

        response = client.get('/entities/')

        assert response.status_code == 500
        assert b'Internal Server Error' in response.data

    @patch('web_app.blueprints.entities.Person')
    def test_error_handling_persons_list(self, mock_person, client):
        """Test error handling on persons list"""
        mock_person.query.order_by.side_effect = Exception("Database error")

        response = client.get('/entities/persons')

        assert response.status_code == 500

    def test_route_methods_not_allowed(self, client):
        """Test that routes only accept GET requests"""
        routes = [
            '/entities/',
            '/entities/persons',
            '/entities/persons/1',
            '/entities/families',
            '/entities/families/1',
            '/entities/places',
            '/entities/places/1',
            '/entities/events',
            '/entities/events/1',
            '/entities/marriages',
            '/entities/marriages/1'
        ]

        for route in routes:
            response = client.post(route)
            assert response.status_code == 405

    def test_blueprint_url_prefix(self, client):
        """Test that all routes have correct /entities prefix"""
        # Test that routes without /entities prefix return 404
        response = client.get('/persons')
        assert response.status_code == 404

        response = client.get('/families')
        assert response.status_code == 404

    @patch('web_app.blueprints.entities.Family')
    def test_family_with_children(self, mock_family, client):
        """Test family detail with children"""
        mock_child1 = Mock()
        mock_child1.id = 1
        mock_child1.given_names = "Child1"
        mock_child1.surname = "Doe"

        mock_child2 = Mock()
        mock_child2.id = 2
        mock_child2.given_names = "Child2"
        mock_child2.surname = "Doe"

        mock_family_obj = Mock()
        mock_family_obj.id = 1
        mock_family_obj.family_identifier = "FAM001"
        mock_family_obj.generation_number = 1
        mock_family_obj.father = None
        mock_family_obj.mother = None
        mock_family_obj.children = [mock_child1, mock_child2]
        mock_family_obj.notes = ""

        mock_family.query.get_or_404.return_value = mock_family_obj

        response = client.get('/entities/families/1')

        assert response.status_code == 200
        assert b'Child1' in response.data
        assert b'Child2' in response.data

    @patch('web_app.blueprints.entities.Person')
    def test_person_without_optional_fields(self, mock_person, client):
        """Test person detail without optional fields"""
        mock_person_obj = Mock()
        mock_person_obj.id = 1
        mock_person_obj.given_names = "Simple"
        mock_person_obj.tussenvoegsel = ""
        mock_person_obj.surname = "Person"
        mock_person_obj.birth_date = ""
        mock_person_obj.baptism_date = ""
        mock_person_obj.death_date = ""
        mock_person_obj.notes = ""

        mock_person.query.get_or_404.return_value = mock_person_obj

        response = client.get('/entities/persons/1')

        assert response.status_code == 200
        assert b'Simple' in response.data
        assert b'Person' in response.data
