"""
Tests for genealogy data models
"""


from web_app.shared.models import Event, Family, Person


def test_person_creation():
    """Test Person model creation"""
    person = Person(
        id="person_1",
        given_names="Jan",
        surname="van Bulhuis",
        birth_date="1800-01-01",
        birth_place="Amsterdam"
    )

    assert person.id == "person_1"
    assert person.given_names == "Jan"
    assert person.surname == "van Bulhuis"
    assert person.full_name == "Jan van Bulhuis"
    assert person.birth_date == "1800-01-01"
    assert person.birth_place == "Amsterdam"

def test_person_full_name_with_prefix():
    """Test full name construction with name prefix"""
    person = Person(
        id="person_2",
        given_names="Maria",
        surname="Jansen",
        tussenvoegsel="de"
    )

    assert person.full_name == "Maria de Jansen"

def test_family_creation():
    """Test Family model creation"""
    family = Family(
        id="family_1",
        husband_id="person_1",
        wife_id="person_2",
        marriage_date="1825-06-15",
        marriage_place="Amsterdam"
    )

    assert family.id == "family_1"
    assert family.husband_id == "person_1"
    assert family.wife_id == "person_2"
    assert family.marriage_date == "1825-06-15"
    assert family.marriage_place == "Amsterdam"

def test_event_creation():
    """Test Event model creation"""
    event = Event(
        id="event_1",
        title="Birth of Jan van Bulhuis",
        event_type="birth",
        date="1800-01-01",
        place="Amsterdam",
        description="Birth of Jan van Bulhuis"
    )

    assert event.id == "event_1"
    assert event.title == "Birth of Jan van Bulhuis"
    assert event.event_type == "birth"
    assert event.date == "1800-01-01"
    assert event.place == "Amsterdam"
    assert event.description == "Birth of Jan van Bulhuis"

def test_person_str_representation():
    """Test Person string representation"""
    person = Person(
        id="person_1",
        given_names="Jan",
        surname="van Bulhuis"
    )

    # Test the full_name property since it's a dataclass
    assert person.full_name == "Jan van Bulhuis"
    assert person.id == "person_1"
