"""
Pure GEDCOM formatting without file I/O operations
"""

from datetime import datetime

from web_app.database.models import Family, Person


class GEDCOMFormatter:
    """Format genealogy data to GEDCOM format without file operations"""

    def __init__(self):
        self.person_counter = 1
        self.family_counter = 1
        self.source_counter = 1

    def format_gedcom(self, people: list[Person], families: list[Family] = None) -> list[str]:
        """Format genealogy data to GEDCOM lines"""
        lines = []

        # GEDCOM header
        lines.extend(self._format_header())

        # Format individuals
        for person in people:
            lines.extend(self._format_individual(person))

        # Format families if provided
        if families:
            for family in families:
                lines.extend(self._format_family(family))

        # GEDCOM trailer
        lines.extend(self._format_trailer())

        return lines

    def _format_header(self) -> list[str]:
        """Format GEDCOM header"""
        return [
            "0 HEAD",
            "1 SOUR VanBulhuisExtractor",
            "2 VERS 1.0",
            "2 NAME Van Bulhuis Family Book Extractor",
            "1 DATE " + datetime.now().strftime("%d %b %Y").upper(),
            "1 FILE family_tree.ged",
            "1 GEDC",
            "2 VERS 5.5.1",
            "2 FORM LINEAGE-LINKED",
            "1 CHAR UTF-8",
            "1 LANG English"
        ]

    def _format_trailer(self) -> list[str]:
        """Format GEDCOM trailer"""
        return ["0 TRLR"]

    def _format_individual(self, person: Person) -> list[str]:
        """Format an individual record"""
        lines = []
        person_id = f"@I{self.person_counter:04d}@"
        self.person_counter += 1

        lines.append(f"0 {person_id} INDI")

        # Name
        if person.given_names or person.surname:
            name_parts = []
            if person.given_names:
                name_parts.append(person.given_names)

            surname_part = ""
            if person.tussenvoegsel:
                surname_part = f"{person.tussenvoegsel} "
            if person.surname:
                surname_part += person.surname

            if surname_part:
                name_parts.append(f"/{surname_part}/")

            name = " ".join(name_parts)
            lines.append(f"1 NAME {name}")

            # Name components
            if person.given_names:
                lines.append(f"2 GIVN {person.given_names}")
            if person.surname:
                lines.append(f"2 SURN {person.surname}")
            if person.tussenvoegsel:
                lines.append(f"2 NPFX {person.tussenvoegsel}")

        # Sex (try to detect from name if not provided)
        sex = getattr(person, 'sex', None)
        if not sex and person.given_names:
            from .dutch_utils import DutchNameParser
            detected_gender = DutchNameParser.detect_gender(person.given_names)
            if detected_gender:
                sex = detected_gender

        if sex:
            lines.append(f"1 SEX {sex}")

        # Birth
        if person.birth_date or person.birth_place:
            lines.append("1 BIRT")
            if person.birth_date:
                lines.append(f"2 DATE {person.birth_date}")
            if person.birth_place:
                lines.append(f"2 PLAC {person.birth_place}")

        # Baptism
        if person.baptism_date or person.baptism_place:
            lines.append("1 BAPM")
            if person.baptism_date:
                lines.append(f"2 DATE {person.baptism_date}")
            if person.baptism_place:
                lines.append(f"2 PLAC {person.baptism_place}")

        # Death
        if person.death_date or person.death_place:
            lines.append("1 DEAT")
            if person.death_date:
                lines.append(f"2 DATE {person.death_date}")
            if person.death_place:
                lines.append(f"2 PLAC {person.death_place}")

        # Occupations
        if hasattr(person, 'occupations') and person.occupations:
            for occupation in person.occupations:
                if occupation.strip():
                    lines.append(f"1 OCCU {occupation}")

        # Notes
        if person.notes and person.notes.strip():
            # Split long notes into multiple lines
            note_lines = self._split_note(person.notes.strip())
            for i, line in enumerate(note_lines):
                if i == 0:
                    lines.append(f"1 NOTE {line}")
                else:
                    lines.append(f"2 CONT {line}")

        return lines

    def _format_family(self, family: Family) -> list[str]:
        """Format a family record"""
        lines = []
        family_id = f"@F{self.family_counter:04d}@"
        self.family_counter += 1

        lines.append(f"0 {family_id} FAM")

        # Husband
        if family.husband_id:
            lines.append(f"1 HUSB @I{family.husband_id}@")

        # Wife
        if family.wife_id:
            lines.append(f"1 WIFE @I{family.wife_id}@")

        # Children
        if family.children_ids:
            for child_id in family.children_ids:
                lines.append(f"1 CHIL @I{child_id}@")

        # Marriage event
        if hasattr(family, 'marriage_date') or hasattr(family, 'marriage_place'):
            lines.append("1 MARR")
            if hasattr(family, 'marriage_date') and family.marriage_date:
                lines.append(f"2 DATE {family.marriage_date}")
            if hasattr(family, 'marriage_place') and family.marriage_place:
                lines.append(f"2 PLAC {family.marriage_place}")

        return lines

    def _split_note(self, note: str, max_length: int = 72) -> list[str]:
        """Split note into lines of maximum length"""
        if len(note) <= max_length:
            return [note]

        lines = []
        words = note.split()
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= max_length:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines


class GEDCOMFileWriter:
    """Handles GEDCOM file I/O operations"""

    @staticmethod
    def write_gedcom_file(lines: list[str], output_file: str) -> None:
        """Write GEDCOM lines to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    @staticmethod
    def read_gedcom_file(input_file: str) -> list[str]:
        """Read GEDCOM lines from file"""
        with open(input_file, encoding='utf-8') as f:
            return f.read().splitlines()
