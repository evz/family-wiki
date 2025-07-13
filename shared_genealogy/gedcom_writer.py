"""
GEDCOM writer for exporting genealogy data to GEDCOM format
"""

from typing import List, Dict, Optional
from datetime import datetime
from .models import Person, Family, Place, Event

class GEDCOMWriter:
    """Write genealogy data to GEDCOM format"""
    
    def __init__(self):
        self.lines = []
        self.person_counter = 1
        self.family_counter = 1
        self.source_counter = 1
        
    def write_gedcom(self, people: List[Person], families: List[Family] = None, 
                     output_file: str = "family_tree.ged") -> None:
        """Write genealogy data to GEDCOM file"""
        
        self.lines = []
        
        # GEDCOM header
        self._write_header()
        
        # Write individuals
        for person in people:
            self._write_individual(person)
        
        # Write families if provided
        if families:
            for family in families:
                self._write_family(family)
        
        # GEDCOM trailer
        self._write_trailer()
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.lines))
    
    def _write_header(self) -> None:
        """Write GEDCOM header"""
        self.lines.extend([
            "0 HEAD",
            "1 SOUR VanBulhuisExtractor",
            "2 VERS 1.0",
            "2 NAME Van Bulhuis Family Book Extractor",
            "2 CORP AI-Powered Genealogy Tools",
            "1 DEST ANY",
            "1 DATE " + datetime.now().strftime("%d %b %Y").upper(),
            "2 TIME " + datetime.now().strftime("%H:%M:%S"),
            "1 SUBM @SUBM1@",
            "1 FILE VanBulhuisFamily.ged",
            "1 GEDC",
            "2 VERS 5.5.1",
            "2 FORM LINEAGE-LINKED",
            "1 CHAR UTF-8",
            "1 LANG Dutch",
            ""
        ])
    
    def _write_individual(self, person: Person) -> None:
        """Write an individual record"""
        person_id = f"@I{self.person_counter:04d}@"
        self.person_counter += 1
        
        self.lines.append(f"0 {person_id} INDI")
        
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
            self.lines.append(f"1 NAME {name}")
            
            # Name components
            if person.given_names:
                self.lines.append(f"2 GIVN {person.given_names}")
            if person.surname:
                self.lines.append(f"2 SURN {person.surname}")
            if person.tussenvoegsel:
                self.lines.append(f"2 NPFX {person.tussenvoegsel}")
        
        # Sex (try to detect from name if not provided)
        sex = getattr(person, 'sex', None)
        if not sex and person.given_names:
            from .dutch_utils import DutchNameParser
            detected_gender = DutchNameParser.detect_gender(person.given_names)
            if detected_gender:
                sex = detected_gender
        
        if sex:
            self.lines.append(f"1 SEX {sex}")
        
        # Birth
        if person.birth_date or person.birth_place:
            self.lines.append("1 BIRT")
            if person.birth_date:
                self.lines.append(f"2 DATE {person.birth_date}")
            if person.birth_place:
                self.lines.append(f"2 PLAC {person.birth_place}")
        
        # Baptism
        if person.baptism_date or person.baptism_place:
            self.lines.append("1 BAPM")
            if person.baptism_date:
                self.lines.append(f"2 DATE {person.baptism_date}")
            if person.baptism_place:
                self.lines.append(f"2 PLAC {person.baptism_place}")
        
        # Death
        if person.death_date or person.death_place:
            self.lines.append("1 DEAT")
            if person.death_date:
                self.lines.append(f"2 DATE {person.death_date}")
            if person.death_place:
                self.lines.append(f"2 PLAC {person.death_place}")
        
        # Occupations
        if person.occupations:
            for occupation in person.occupations:
                if occupation.strip():
                    self.lines.append(f"1 OCCU {occupation}")
        
        # Residences
        if person.residences:
            for residence in person.residences:
                self.lines.append("1 RESI")
                if residence.get('place'):
                    self.lines.append(f"2 PLAC {residence['place']}")
                if residence.get('start_date'):
                    self.lines.append(f"2 DATE {residence['start_date']}")
                if residence.get('notes'):
                    self.lines.append(f"2 NOTE {residence['notes']}")
        
        # Notes
        if person.notes and person.notes.strip():
            # Split long notes into multiple lines
            note_lines = self._split_note(person.notes.strip())
            for i, line in enumerate(note_lines):
                if i == 0:
                    self.lines.append(f"1 NOTE {line}")
                else:
                    self.lines.append(f"2 CONT {line}")
        
        # Sources
        if person.sources:
            for source in person.sources:
                if source.strip():
                    self.lines.append(f"1 SOUR {source}")
        
        # Confidence as note if present
        if hasattr(person, 'confidence_score') and person.confidence_score > 0:
            self.lines.append(f"1 NOTE Extraction confidence: {person.confidence_score:.2f}")
        
        self.lines.append("")  # Empty line between records
    
    def _write_family(self, family: Family) -> None:
        """Write a family record"""
        family_id = f"@F{self.family_counter:04d}@"
        self.family_counter += 1
        
        self.lines.append(f"0 {family_id} FAM")
        
        if family.husband_id:
            self.lines.append(f"1 HUSB @{family.husband_id}@")
        
        if family.wife_id:
            self.lines.append(f"1 WIFE @{family.wife_id}@")
        
        for child_id in family.children_ids:
            self.lines.append(f"1 CHIL @{child_id}@")
        
        # Marriage
        if family.marriage_date or family.marriage_place:
            self.lines.append("1 MARR")
            if family.marriage_date:
                self.lines.append(f"2 DATE {family.marriage_date}")
            if family.marriage_place:
                self.lines.append(f"2 PLAC {family.marriage_place}")
        
        # Divorce
        if family.divorce_date:
            self.lines.append("1 DIV")
            self.lines.append(f"2 DATE {family.divorce_date}")
        
        # Notes
        if family.notes and family.notes.strip():
            note_lines = self._split_note(family.notes.strip())
            for i, line in enumerate(note_lines):
                if i == 0:
                    self.lines.append(f"1 NOTE {line}")
                else:
                    self.lines.append(f"2 CONT {line}")
        
        self.lines.append("")  # Empty line between records
    
    def _write_trailer(self) -> None:
        """Write GEDCOM trailer"""
        self.lines.extend([
            "0 @SUBM1@ SUBM",
            "1 NAME Van Bulhuis Family Researcher",
            "1 ADDR Unknown",
            "",
            "0 TRLR"
        ])
    
    def _split_note(self, note: str, max_length: int = 248) -> List[str]:
        """Split long notes into GEDCOM-compliant lines"""
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
    
    def create_gedcom_from_llm_results(self, llm_results_file: str, 
                                       output_file: str = "family_tree.ged") -> None:
        """Create GEDCOM from LLM extraction results"""
        import json
        
        with open(llm_results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        people = []
        for person_data in data.get('people', []):
            person = Person(
                id=f"I{len(people) + 1:04d}",
                given_names=person_data.get('given_names', ''),
                surname=person_data.get('surname', ''),
                birth_date=person_data.get('birth_date', ''),
                birth_place=person_data.get('birth_place', ''),
                baptism_date=person_data.get('baptism_date', ''),
                baptism_place=person_data.get('baptism_place', ''),
                death_date=person_data.get('death_date', ''),
                death_place=person_data.get('death_place', ''),
                notes=person_data.get('notes', ''),
                confidence_score=person_data.get('confidence', 0.0)
            )
            
            # Parse Dutch name components
            if person_data.get('surname'):
                from .dutch_utils import DutchNameParser
                given, tussenvoegsel, surname = DutchNameParser.parse_full_name(
                    f"{person.given_names} {person_data['surname']}")
                person.given_names = given
                person.tussenvoegsel = tussenvoegsel
                person.surname = surname
            
            people.append(person)
        
        self.write_gedcom(people, output_file=output_file)
        print(f"GEDCOM file created: {output_file}")
        print(f"Total individuals: {len(people)}")
    
    def validate_gedcom(self, file_path: str) -> Dict:
        """Basic GEDCOM validation"""
        issues = []
        line_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                line_count = i
                line = line.strip()
                
                if not line:
                    continue
                
                # Check level format
                if not line[0].isdigit():
                    issues.append(f"Line {i}: Invalid level format")
                
                # Check for required tags
                if line.startswith('0 ') and not any(tag in line for tag in ['HEAD', 'INDI', 'FAM', 'SUBM', 'TRLR']):
                    if '@' not in line:
                        issues.append(f"Line {i}: Unknown level 0 record")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'line_count': line_count
            }
            
        except Exception as e:
            return {
                'valid': False,
                'issues': [f"File reading error: {e}"],
                'line_count': 0
            }