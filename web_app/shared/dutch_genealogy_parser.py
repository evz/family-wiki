"""
Dutch genealogy data parsing utilities - separated from business logic
"""

import re

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)


class DutchGenealogyParser:
    """Parser for Dutch genealogy data"""

    # Common Dutch name particles (tussenvoegsel)
    DUTCH_PARTICLES = [
        'van', 'de', 'der', 'den', 'van de', 'van der', 'van den',
        'op', 'op de', 'op den', 'op het', 'in', 'in de', 'in der',
        'uit', 'uit de', 'uit den', 'te', 'ter', 'ten', 'tot',
        'voor', 'voor de', 'bij', 'bij de', 'onder', 'onder de'
    ]

    # Common Dutch date patterns
    DATE_PATTERNS = [
        r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
        r'(\d{1,2})\.(\d{1,2})\.(\d{4})', # DD.MM.YYYY
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # DD Month YYYY
    ]

    # Dutch month names
    DUTCH_MONTHS = {
        'januari': '01', 'februari': '02', 'maart': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'augustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mrt': '03', 'apr': '04',
        'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
        'okt': '10', 'nov': '11', 'dec': '12'
    }

    @classmethod
    def parse_dutch_name(cls, name_str: str) -> tuple[str, str, str]:
        """Parse Dutch name into given_names, tussenvoegsel, surname"""
        if not name_str:
            return "", "", ""

        name_str = name_str.strip()
        if not name_str:
            return "", "", ""

        parts = name_str.split()

        if len(parts) == 1:
            # Single name - assume it's a given name
            return parts[0], "", ""

        if len(parts) == 2:
            # Two parts - given name and surname
            return parts[0], "", parts[1]

        # Three or more parts - need to identify tussenvoegsel
        # Start by assuming all parts are given names, then find tussenvoegsel
        given_names_parts = []
        tussenvoegsel = ""
        surname_parts = []

        i = 0
        while i < len(parts):
            # Try to match particles of different lengths starting from current position
            found_particle = False
            for particle_length in range(min(3, len(parts) - i), 0, -1):
                potential_particle = " ".join(parts[i:i + particle_length])
                if potential_particle.lower() in cls.DUTCH_PARTICLES:
                    # Found a particle - everything before this is given names
                    given_names_parts = parts[:i]
                    # Collect all particles
                    if tussenvoegsel:
                        tussenvoegsel += " "
                    tussenvoegsel += potential_particle
                    i += particle_length
                    found_particle = True
                    break

            if not found_particle:
                if tussenvoegsel:
                    # We already found particles, remaining parts are surname
                    surname_parts = parts[i:]
                    break
                else:
                    # No particles found yet, continue
                    i += 1

        # If no particles were found, treat last part as surname and rest as given names
        if not tussenvoegsel:
            if len(parts) > 1:
                given_names_parts = parts[:-1]
                surname_parts = [parts[-1]]
            else:
                given_names_parts = parts
                surname_parts = []

        given_names = " ".join(given_names_parts)
        surname = " ".join(surname_parts)

        return given_names, tussenvoegsel, surname

    @classmethod
    def parse_dutch_date(cls, date_str: str) -> str:
        """Parse Dutch date string to ISO format (YYYY-MM-DD)"""
        if not date_str:
            return ""

        date_str = date_str.strip().lower()

        # Try each pattern
        for pattern in cls.DATE_PATTERNS:
            match = re.match(pattern, date_str)
            if match:
                groups = match.groups()

                # Handle different formats
                if len(groups) == 3:
                    if pattern.startswith(r'(\d{4})'):
                        # YYYY-MM-DD format
                        year, month, day = groups
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif r'(\w+)' in pattern:
                        # DD Month YYYY format
                        day, month_name, year = groups
                        month = cls.DUTCH_MONTHS.get(month_name, month_name)
                        if month.isdigit():
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:
                        # DD-MM-YYYY format
                        day, month, year = groups
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # If no pattern matches, return as-is
        logger.warning(f"Could not parse date: {date_str}")
        return date_str

    @classmethod
    def normalize_place_name(cls, place_str: str) -> str:
        """Normalize Dutch place name"""
        if not place_str:
            return ""

        place_str = place_str.strip()

        # Remove common prefixes/suffixes
        place_str = re.sub(r'^(te|in|op|bij)\s+', '', place_str, flags=re.IGNORECASE)
        place_str = re.sub(r'\s+(nederland|holland|nl)$', '', place_str, flags=re.IGNORECASE)

        # Capitalize first letter of each word
        place_str = ' '.join(word.capitalize() for word in place_str.split())

        return place_str

    @classmethod
    def extract_generation_info(cls, text: str) -> int | None:
        """Extract generation number from text"""
        if not text:
            return None

        # Look for generation indicators
        patterns = [
            r'(\d+)e?\s*generatie',
            r'generatie\s*(\d+)',
            r'gen\.?\s*(\d+)',
            r'(\d+)e?\s*gen\.?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue

        return None

    @classmethod
    def parse_family_relationships(cls, text: str) -> dict[str, list[str]]:
        """Parse family relationship indicators from text"""
        relationships = {
            'children': [],
            'parents': [],
            'spouses': [],
            'siblings': []
        }

        if not text:
            return relationships

        text_lower = text.lower()

        # Look for children indicators
        children_patterns = [
            r'kinderen van',
            r'zoon van',
            r'dochter van',
            r'kind van',
            r'zonen en dochters',
        ]

        for pattern in children_patterns:
            if re.search(pattern, text_lower):
                relationships['children'].append(pattern)

        # Look for marriage indicators
        marriage_patterns = [
            r'gehuwd met',
            r'getrouwd met',
            r'huwelijk met',
            r'echtgenoot',
            r'echtgenote',
            r'vrouw van',
            r'man van',
        ]

        for pattern in marriage_patterns:
            if re.search(pattern, text_lower):
                relationships['spouses'].append(pattern)

        return relationships

    @classmethod
    def calculate_summary_statistics(cls, families: list[dict],
                                   isolated_individuals: list[dict]) -> dict[str, int]:
        """Calculate summary statistics from extraction data"""
        stats = {
            'total_families': len(families),
            'total_isolated_individuals': len(isolated_individuals),
            'total_people': len(isolated_individuals),
            'total_children': 0,
            'total_parents': 0,
            'generations_found': set(),
            'average_confidence': 0.0
        }

        confidence_scores = []

        # Process families
        for family in families:
            # Count parents
            if 'parents' in family:
                if 'father' in family['parents']:
                    stats['total_parents'] += 1
                    stats['total_people'] += 1
                if 'mother' in family['parents']:
                    stats['total_parents'] += 1
                    stats['total_people'] += 1

            # Count children
            if 'children' in family:
                child_count = len(family['children'])
                stats['total_children'] += child_count
                stats['total_people'] += child_count

            # Track generation
            if 'generation' in family:
                gen = cls.extract_generation_info(str(family['generation']))
                if gen:
                    stats['generations_found'].add(gen)

            # Track confidence
            if 'confidence_score' in family:
                confidence_scores.append(family['confidence_score'])

        # Process isolated individuals
        for individual in isolated_individuals:
            # Track generation
            if 'generation' in individual:
                gen = cls.extract_generation_info(str(individual['generation']))
                if gen:
                    stats['generations_found'].add(gen)

            # Track confidence
            if 'confidence_score' in individual:
                confidence_scores.append(individual['confidence_score'])

        # Calculate averages
        if confidence_scores:
            stats['average_confidence'] = sum(confidence_scores) / len(confidence_scores)

        # Convert generations set to count
        stats['generations_count'] = len(stats['generations_found'])
        del stats['generations_found']  # Remove set for JSON serialization

        return stats
