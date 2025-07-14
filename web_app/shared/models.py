"""
Shared data models for genealogy processing
"""

from dataclasses import dataclass, field


@dataclass
class Person:
    """Represents a person in the family tree"""
    id: str
    given_names: str = ""
    surname: str = ""
    tussenvoegsel: str = ""  # Dutch particles (van, de, etc.)

    # Life events
    birth_date: str = ""
    birth_place: str = ""
    baptism_date: str = ""
    baptism_place: str = ""
    death_date: str = ""
    death_place: str = ""

    # Relationships
    marriages: list[dict] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)

    # Additional info
    occupations: list[str] = field(default_factory=list)
    residences: list[dict] = field(default_factory=list)
    notes: str = ""
    sources: list[str] = field(default_factory=list)
    confidence_score: float = 0.0

    @property
    def full_name(self) -> str:
        """Get full name with proper Dutch formatting"""
        parts = [self.given_names]
        if self.tussenvoegsel:
            parts.append(self.tussenvoegsel)
        if self.surname:
            parts.append(self.surname)
        return " ".join(filter(None, parts))

    @property
    def display_name(self) -> str:
        """Get display name (surname, given names)"""
        if self.surname and self.given_names:
            surname_part = f"{self.tussenvoegsel} {self.surname}".strip() if self.tussenvoegsel else self.surname
            return f"{surname_part}, {self.given_names}"
        return self.full_name

    def add_marriage(self, spouse_id: str, date: str = "", place: str = "", notes: str = ""):
        """Add a marriage record"""
        marriage = {
            'spouse_id': spouse_id,
            'date': date,
            'place': place,
            'notes': notes
        }
        self.marriages.append(marriage)

    def add_residence(self, place: str, start_date: str = "", end_date: str = "", notes: str = ""):
        """Add a residence record"""
        residence = {
            'place': place,
            'start_date': start_date,
            'end_date': end_date,
            'notes': notes
        }
        self.residences.append(residence)

@dataclass
class Family:
    """Represents a family unit (parents + children)"""
    id: str
    husband_id: str | None = None
    wife_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    marriage_date: str = ""
    marriage_place: str = ""
    divorce_date: str = ""
    notes: str = ""

@dataclass
class Place:
    """Represents a geographic location with family significance"""
    name: str
    country: str = ""
    region: str = ""
    coordinates: str = ""
    description: str = ""
    historical_context: str = ""
    family_connections: list[dict] = field(default_factory=list)

    def add_family_connection(self, person_id: str, connection_type: str, date: str = "", notes: str = ""):
        """Add a family connection to this place"""
        connection = {
            'person_id': person_id,
            'connection_type': connection_type,  # birth, death, marriage, residence
            'date': date,
            'notes': notes
        }
        self.family_connections.append(connection)

@dataclass
class Event:
    """Represents a family event (wedding, reunion, etc.)"""
    id: str
    title: str
    event_type: str  # wedding, reunion, birth, death, etc.
    date: str = ""
    place: str = ""
    description: str = ""
    participants: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def add_participant(self, person_id: str, role: str = ""):
        """Add a participant to the event"""
        if isinstance(self.participants, list):
            if not any(p.get('person_id') == person_id for p in self.participants if isinstance(p, dict)):
                self.participants.append({
                    'person_id': person_id,
                    'role': role
                })
        else:
            # Handle legacy list of strings
            if person_id not in self.participants:
                self.participants.append(person_id)

@dataclass
class Source:
    """Represents a genealogical source"""
    id: str
    title: str
    source_type: str  # book, document, website, etc.
    author: str = ""
    publication_date: str = ""
    location: str = ""
    url: str = ""
    notes: str = ""
    confidence: str = ""  # primary, secondary, etc.
