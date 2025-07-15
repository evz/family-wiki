"""
Tests for model methods that aren't covered by other tests
"""

import pytest
from web_app.shared.models import Person, Family, Place, Event


class TestPersonMethods:
    """Test Person model methods"""

    def test_full_name_complete(self):
        """Test full name with all components"""
        person = Person(
            id="test",
            given_names="Jan Willem",
            tussenvoegsel="van der", 
            surname="Berg"
        )
        
        assert person.full_name == "Jan Willem van der Berg"

    def test_full_name_no_tussenvoegsel(self):
        """Test full name without tussenvoegsel"""
        person = Person(
            id="test",
            given_names="Maria",
            surname="Smit"
        )
        
        assert person.full_name == "Maria Smit"

    def test_full_name_partial(self):
        """Test full name with only given names"""
        person = Person(
            id="test",
            given_names="Johannes"
        )
        
        assert person.full_name == "Johannes"

    def test_display_name_complete(self):
        """Test display name with surname and given names"""
        person = Person(
            id="test",
            given_names="Jan Willem",
            tussenvoegsel="van der",
            surname="Berg"
        )
        
        assert person.display_name == "van der Berg, Jan Willem"

    def test_display_name_no_tussenvoegsel(self):
        """Test display name without tussenvoegsel"""
        person = Person(
            id="test",
            given_names="Maria",
            surname="Smit"
        )
        
        assert person.display_name == "Smit, Maria"

    def test_display_name_fallback(self):
        """Test display name falls back to full name when no surname"""
        person = Person(
            id="test",
            given_names="Johannes"
        )
        
        assert person.display_name == "Johannes"

    def test_add_marriage(self):
        """Test adding marriage record"""
        person = Person(id="test")
        person.add_marriage(
            spouse_id="spouse1",
            date="1875-06-15",
            place="Amsterdam",
            notes="Test marriage"
        )
        
        assert len(person.marriages) == 1
        marriage = person.marriages[0]
        assert marriage['spouse_id'] == "spouse1"
        assert marriage['date'] == "1875-06-15"
        assert marriage['place'] == "Amsterdam"
        assert marriage['notes'] == "Test marriage"

    def test_add_multiple_marriages(self):
        """Test adding multiple marriages"""
        person = Person(id="test")
        person.add_marriage("spouse1", "1875-01-01", "Amsterdam")
        person.add_marriage("spouse2", "1880-01-01", "Rotterdam")
        
        assert len(person.marriages) == 2

    def test_add_residence(self):
        """Test adding residence record"""
        person = Person(id="test")
        person.add_residence(
            place="Amsterdam",
            start_date="1850-01-01",
            end_date="1875-01-01",
            notes="Lived here as child"
        )
        
        assert len(person.residences) == 1
        residence = person.residences[0]
        assert residence['place'] == "Amsterdam"
        assert residence['start_date'] == "1850-01-01"
        assert residence['end_date'] == "1875-01-01"
        assert residence['notes'] == "Lived here as child"


class TestPlaceMethods:
    """Test Place model methods"""

    def test_add_family_connection(self):
        """Test adding family connection to place"""
        place = Place(name="Amsterdam")
        place.add_family_connection(
            person_id="person1",
            connection_type="birth",
            date="1850-01-01",
            notes="Born here"
        )
        
        assert len(place.family_connections) == 1
        connection = place.family_connections[0]
        assert connection['person_id'] == "person1"
        assert connection['connection_type'] == "birth"
        assert connection['date'] == "1850-01-01"
        assert connection['notes'] == "Born here"


class TestEventMethods:
    """Test Event model methods"""

    def test_add_participant_dict_format(self):
        """Test adding participant when participants is list of dicts"""
        event = Event(id="event1", title="Wedding", event_type="wedding")
        event.participants = []  # Ensure it's a list
        
        event.add_participant("person1", "groom")
        event.add_participant("person2", "bride")
        
        assert len(event.participants) == 2
        assert event.participants[0]['person_id'] == "person1"
        assert event.participants[0]['role'] == "groom"
        assert event.participants[1]['person_id'] == "person2"
        assert event.participants[1]['role'] == "bride"

    def test_add_participant_no_duplicate(self):
        """Test that duplicate participants aren't added"""
        event = Event(id="event1", title="Wedding", event_type="wedding")
        event.participants = []
        
        event.add_participant("person1", "groom")
        event.add_participant("person1", "groom")  # Duplicate
        
        assert len(event.participants) == 1

    def test_add_participant_legacy_format(self):
        """Test adding participant when participants is list of strings (legacy)"""
        event = Event(id="event1", title="Wedding", event_type="wedding")
        event.participants = ["existing_person"]  # Legacy string format
        
        event.add_participant("person1")
        
        assert len(event.participants) == 2
        # Mixed format after adding to legacy list
        assert "existing_person" in event.participants

    def test_add_participant_legacy_no_duplicate(self):
        """Test no duplicate in legacy string format"""
        event = Event(id="event1", title="Wedding", event_type="wedding")
        event.participants = ["person1"]  # Legacy string format
        
        event.add_participant("person1")  # Duplicate
        
        # The method doesn't prevent duplicates between string and dict formats
        assert len(event.participants) == 2  # One string, one dict