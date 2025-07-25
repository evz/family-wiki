"""
GEDCOM writer for exporting genealogy data to GEDCOM format
"""

from web_app.database.models import Family, Person

from .gedcom_formatter import GEDCOMFileWriter, GEDCOMFormatter


class GEDCOMWriter:
    """Write genealogy data to GEDCOM format"""

    def __init__(self):
        self.formatter = GEDCOMFormatter()
        self.file_writer = GEDCOMFileWriter()

    def write_gedcom(self, people: list[Person], families: list[Family] = None,
                     output_file: str = "family_tree.ged") -> None:
        """Write genealogy data to GEDCOM file"""
        # Format the data
        lines = self.formatter.format_gedcom(people, families)

        # Write to file
        self.file_writer.write_gedcom_file(lines, output_file)

    def generate(self) -> str:
        """Generate GEDCOM content as string for backward compatibility"""
        # This method exists for backward compatibility with existing code
        people = getattr(self, 'people', None)
        families = getattr(self, 'families', None)
        lines = self.formatter.format_gedcom(people, families)
        return '\n'.join(lines)

    def add_person(self, person: Person) -> None:
        """Add person for backward compatibility"""
        if not hasattr(self, 'people'):
            self.people = []
        self.people.append(person)

    def add_family(self, family: Family) -> None:
        """Add family for backward compatibility"""
        if not hasattr(self, 'families'):
            self.families = []
        self.families.append(family)
