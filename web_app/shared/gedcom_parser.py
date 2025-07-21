"""
GEDCOM parser for reading genealogy data from GEDCOM files
"""

import re

from .dutch_utils import DutchDateParser, DutchNameParser


class GEDCOMParser:
    """Parse GEDCOM files into structured data dictionaries"""

    def __init__(self):
        """Initialize parser"""
        # Raw GEDCOM data storage
        self.raw_person_data = {}
        self.raw_family_data = {}

    def parse_file(self, file_path: str) -> dict:
        """Parse a GEDCOM file and return structured data"""
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

        records = self._split_into_records(lines)

        # Parse all records and collect data
        for record in records:
            self._parse_record_first_pass(record)

        return {
            'persons': self.raw_person_data,
            'families': self.raw_family_data
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

    def _parse_record_first_pass(self, record: list[str]) -> None:
        """First pass: collect raw GEDCOM data"""
        if not record:
            return

        header = record[0]

        if '@' in header and 'INDI' in header:
            self._collect_individual_data(record)
        elif '@' in header and 'FAM' in header:
            self._collect_family_data(record)

    def _collect_individual_data(self, record: list[str]) -> None:
        """Collect raw individual data for first pass"""
        header = record[0]
        person_id = self._extract_id(header)

        if not person_id:
            return

        person_data = {
            'gedcom_id': person_id,
            'notes': '',
            'occupations': []
        }

        i = 1
        while i < len(record):
            line = record[i]
            level = self._get_level(line)
            tag = self._get_tag(line)
            value = self._get_value(line)

            if level == 1:
                if tag == 'NAME':
                    given_names, tussenvoegsel, surname = DutchNameParser.parse_full_name(value)
                    person_data['given_names'] = given_names
                    person_data['tussenvoegsel'] = tussenvoegsel
                    person_data['surname'] = surname
                elif tag == 'SEX':
                    person_data['sex'] = value
                elif tag in ['BIRT', 'BAPM', 'DEAT']:
                    event_data = self._parse_event_subrecord(record, i)
                    if tag == 'BIRT':
                        person_data['birth_date'] = event_data.get('date', '')
                        person_data['birth_place'] = event_data.get('place', '')
                    elif tag == 'BAPM':
                        person_data['baptism_date'] = event_data.get('date', '')
                        person_data['baptism_place'] = event_data.get('place', '')
                    elif tag == 'DEAT':
                        person_data['death_date'] = event_data.get('date', '')
                        person_data['death_place'] = event_data.get('place', '')
                elif tag == 'OCCU':
                    person_data['occupations'].append(value)
                elif tag == 'NOTE':
                    person_data['notes'] += value + " "

            i += 1

        self.raw_person_data[person_id] = person_data

    def _collect_family_data(self, record: list[str]) -> None:
        """Collect raw family data for first pass"""
        header = record[0]
        family_id = self._extract_id(header)

        if not family_id:
            return

        family_data = {
            'gedcom_id': family_id,
            'husband_gedcom_id': None,
            'wife_gedcom_id': None,
            'children_gedcom_ids': [],
            'marriage_date': '',
            'marriage_place': ''
        }

        i = 1
        while i < len(record):
            line = record[i]
            level = self._get_level(line)
            tag = self._get_tag(line)
            value = self._get_value(line)

            if level == 1:
                if tag == 'HUSB':
                    family_data['husband_gedcom_id'] = self._extract_id(value)
                elif tag == 'WIFE':
                    family_data['wife_gedcom_id'] = self._extract_id(value)
                elif tag == 'CHIL':
                    family_data['children_gedcom_ids'].append(self._extract_id(value))
                elif tag == 'MARR':
                    # Parse marriage event sub-records
                    event_data = self._parse_event_subrecord(record, i)
                    family_data['marriage_date'] = event_data.get('date', '')
                    family_data['marriage_place'] = event_data.get('place', '')

            i += 1

        self.raw_family_data[family_id] = family_data


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

    def get_person_data(self, gedcom_id: str) -> dict | None:
        """Get parsed person data by GEDCOM ID"""
        return self.raw_person_data.get(gedcom_id)

    def get_family_data(self, gedcom_id: str) -> dict | None:
        """Get parsed family data by GEDCOM ID"""
        return self.raw_family_data.get(gedcom_id)
