"""
GEDCOM parser for reading genealogy data from GEDCOM files
"""

import re

from .dutch_utils import DutchDateParser, DutchNameParser


# Temporarily disabled - needs refactor to use SQLAlchemy models
# from .models import Family, Person


class GEDCOMParser:
    """Parse GEDCOM files into structured genealogy data"""

    def __init__(self):
        self.individuals = {}
        self.families = {}
        self.places = {}
        self.events = {}
        self.sources = {}

    def parse_file(self, file_path: str) -> dict:
        """Parse a GEDCOM file and return structured data"""
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        records = self._split_into_records(lines)

        for record in records:
            self._parse_record(record)

        return {
            'individuals': self.individuals,
            'families': self.families,
            'places': self.places,
            'events': self.events,
            'sources': self.sources
        }

    def _split_into_records(self, lines: list[str]) -> list[list[str]]:
        """Split GEDCOM lines into individual records"""
        records = []
        current_record = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            level = self._get_level(line)

            if level == 0 and current_record:
                records.append(current_record)
                current_record = []

            current_record.append(line)

        if current_record:
            records.append(current_record)

        return records

    def _get_level(self, line: str) -> int:
        """Extract the level number from a GEDCOM line"""
        match = re.match(r'^(\d+)', line)
        return int(match.group(1)) if match else 0

    def _parse_record(self, record: list[str]) -> None:
        """Parse a single GEDCOM record"""
        if not record:
            return

        header = record[0]

        if '@' in header and 'INDI' in header:
            self._parse_individual_record(record)
        elif '@' in header and 'FAM' in header:
            self._parse_family_record(record)
        elif '@' in header and 'SOUR' in header:
            self._parse_source_record(record)

    def _parse_individual_record(self, record: list[str]) -> None:
        """Parse an individual (INDI) record"""
        header = record[0]
        person_id = self._extract_id(header)

        if not person_id:
            return

        person = Person(id=person_id)

        i = 1
        while i < len(record):
            line = record[i]
            level = self._get_level(line)
            tag = self._get_tag(line)
            value = self._get_value(line)

            if level == 1:
                if tag == 'NAME':
                    given_names, tussenvoegsel, surname = DutchNameParser.parse_full_name(value)
                    person.given_names = given_names
                    person.tussenvoegsel = tussenvoegsel
                    person.surname = surname
                elif tag == 'SEX':
                    person.sex = value
                elif tag in ['BIRT', 'BAPM', 'DEAT']:
                    event_data = self._parse_event_subrecord(record, i)
                    if tag == 'BIRT':
                        person.birth_date = event_data.get('date', '')
                        person.birth_place = event_data.get('place', '')
                    elif tag == 'BAPM':
                        person.baptism_date = event_data.get('date', '')
                        person.baptism_place = event_data.get('place', '')
                    elif tag == 'DEAT':
                        person.death_date = event_data.get('date', '')
                        person.death_place = event_data.get('place', '')
                elif tag == 'OCCU':
                    person.occupations.append(value)
                elif tag == 'NOTE':
                    person.notes += value + " "

            i += 1

        self.individuals[person_id] = person

    def _parse_family_record(self, record: list[str]) -> None:
        """Parse a family (FAM) record"""
        header = record[0]
        family_id = self._extract_id(header)

        if not family_id:
            return

        family = Family(id=family_id)

        for line in record[1:]:
            level = self._get_level(line)
            tag = self._get_tag(line)
            value = self._get_value(line)

            if level == 1:
                if tag == 'HUSB':
                    family.husband_id = self._extract_id(value)
                elif tag == 'WIFE':
                    family.wife_id = self._extract_id(value)
                elif tag == 'CHIL':
                    family.children_ids.append(self._extract_id(value))
                elif tag == 'MARR':
                    # Marriage event - would need to parse sub-records
                    pass

        self.families[family_id] = family

    def _parse_source_record(self, record: list[str]) -> None:
        """Parse a source (SOUR) record"""
        # Implementation for source records
        pass

    def _parse_event_subrecord(self, record: list[str], start_index: int) -> dict:
        """Parse event sub-records (DATE, PLAC, etc.)"""
        event_data = {}

        i = start_index + 1
        while i < len(record):
            line = record[i]
            level = self._get_level(line)

            if level <= 1:
                break

            tag = self._get_tag(line)
            value = self._get_value(line)

            if tag == 'DATE':
                event_data['date'] = DutchDateParser.parse_dutch_date(value)
            elif tag == 'PLAC':
                event_data['place'] = value
            elif tag == 'NOTE':
                event_data['note'] = value

            i += 1

        return event_data

    def _extract_id(self, line: str) -> str | None:
        """Extract ID from a GEDCOM line (e.g., @I001@ INDI)"""
        match = re.search(r'@([^@]+)@', line)
        return match.group(1) if match else None

    def _get_tag(self, line: str) -> str:
        """Extract the tag from a GEDCOM line"""
        parts = line.split()
        return parts[1] if len(parts) > 1 else ''

    def _get_value(self, line: str) -> str:
        """Extract the value from a GEDCOM line"""
        parts = line.split(None, 2)
        return parts[2] if len(parts) > 2 else ''

    def get_person_by_id(self, person_id: str):  # -> Person | None:
        """Get a person by their ID"""
        return self.individuals.get(person_id)

    def get_family_by_id(self, family_id: str):  # -> Family | None:
        """Get a family by their ID"""
        return self.families.get(family_id)

    def get_person_families(self, person_id: str):  # -> list[Family]:
        """Get all families a person belongs to"""
        families = []
        for family in self.families.values():
            if (family.husband_id == person_id or
                family.wife_id == person_id or
                person_id in family.children_ids):
                families.append(family)
        return families
