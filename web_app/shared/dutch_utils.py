"""
Dutch genealogy utilities for names, dates, and places
"""

import re


class DutchNameParser:
    """Handles Dutch naming conventions and particles"""

    # Dutch particles (tussenvoegsel)
    PARTICLES = [
        'van', 'de', 'der', 'den', 'van der', 'van den', 'van de',
        'te', 'tot', 'van \'t', '\'t', 'op', 'onder', 'aan', 'bij'
    ]

    # Common Dutch given names for gender detection
    MALE_NAMES = {
        'johannes', 'jan', 'pieter', 'willem', 'hendrik', 'dirk', 'gerrit',
        'cornelis', 'jacobus', 'nicolaas', 'adrianus', 'petrus', 'antonius',
        'aart', 'leendert', 'sander', 'arie', 'ariën', 'bessel', 'klaas'
    }

    FEMALE_NAMES = {
        'maria', 'anna', 'elisabeth', 'catharina', 'margaretha', 'johanna',
        'hendrika', 'cornelia', 'petronella', 'geertje', 'neeltje', 'arieken',
        'hermina', 'hermijn', 'lijsbet', 'willemijntje', 'gijsje', 'grietje'
    }

    @classmethod
    def parse_full_name(cls, full_name: str) -> tuple[str, str, str]:
        """
        Parse Dutch full name into given names, tussenvoegsel, and surname
        Returns: (given_names, tussenvoegsel, surname)
        """
        if not full_name:
            return "", "", ""

        # Clean up the name
        name = re.sub(r'\s+', ' ', full_name.strip())

        # Handle GEDCOM format "Given names /Surname/"
        gedcom_match = re.match(r'(.+?)\s*/([^/]*)/?\s*', name)
        if gedcom_match:
            given_part = gedcom_match.group(1).strip()
            surname_part = gedcom_match.group(2).strip()

            # Check if surname part contains particles
            given_names, tussenvoegsel = cls._extract_particles_from_given(given_part)

            if not tussenvoegsel:
                # Check if particles are in surname part
                tussenvoegsel, surname = cls._extract_particles_from_surname(surname_part)
            else:
                surname = surname_part

            return given_names, tussenvoegsel, surname

        # Handle "Surname, Given names" format
        if ',' in name:
            surname_part, given_part = name.split(',', 1)
            surname_part = surname_part.strip()
            given_part = given_part.strip()

            tussenvoegsel, surname = cls._extract_particles_from_surname(surname_part)
            given_names = given_part

            return given_names, tussenvoegsel, surname

        # Handle regular "Given names Surname" format
        words = name.split()
        if len(words) < 2:
            return name, "", ""

        # Look for particles in the name
        particle_positions = []
        for i, word in enumerate(words):
            if word.lower() in cls.PARTICLES:
                particle_positions.append(i)

        if particle_positions:
            # Find the best split point
            particle_start = min(particle_positions)
            given_names = ' '.join(words[:particle_start])
            tussenvoegsel = ' '.join(words[particle_start:-1])
            surname = words[-1]
        else:
            # No particles found, assume last word is surname
            given_names = ' '.join(words[:-1])
            tussenvoegsel = ""
            surname = words[-1]

        return given_names, tussenvoegsel, surname

    @classmethod
    def _extract_particles_from_given(cls, given_part: str) -> tuple[str, str]:
        """Extract particles from the given names part"""
        words = given_part.split()
        particle_words = []
        given_words = []

        # Check each word to see if it's a particle
        for word in words:
            if word.lower() in cls.PARTICLES:
                particle_words.append(word)
            else:
                if particle_words:
                    # We've started collecting particles, everything after is surname-related
                    break
                given_words.append(word)

        given_names = ' '.join(given_words)
        tussenvoegsel = ' '.join(particle_words)

        return given_names, tussenvoegsel

    @classmethod
    def _extract_particles_from_surname(cls, surname_part: str) -> tuple[str, str]:
        """Extract particles from the surname part"""
        words = surname_part.split()
        particle_words = []
        surname_words = []

        for word in words:
            if word.lower() in cls.PARTICLES and not surname_words:
                # Particles come before the actual surname
                particle_words.append(word)
            else:
                surname_words.append(word)

        tussenvoegsel = ' '.join(particle_words)
        surname = ' '.join(surname_words)

        return tussenvoegsel, surname

    @classmethod
    def detect_gender(cls, given_names: str) -> str | None:
        """
        Detect gender from Dutch given names
        Returns: 'M', 'F', or None
        """
        if not given_names:
            return None

        # Check first given name
        first_name = given_names.split()[0].lower()

        if first_name in cls.MALE_NAMES:
            return 'M'
        elif first_name in cls.FEMALE_NAMES:
            return 'F'

        # Check for common endings
        if first_name.endswith(('a', 'e', 'je', 'tje')):
            return 'F'

        return None

    @classmethod
    def standardize_name(cls, name: str) -> str:
        """Standardize Dutch name capitalization and spacing"""
        if not name:
            return ""

        # Split into words and capitalize appropriately
        words = name.split()
        standardized = []

        for word in words:
            word_lower = word.lower()

            # Particles should be lowercase
            if word_lower in cls.PARTICLES:
                standardized.append(word_lower)
            # Apostrophes need special handling
            elif "'" in word:
                parts = word.split("'")
                standardized.append("'".join([p.capitalize() if p else p for p in parts]))
            else:
                standardized.append(word.capitalize())

        return ' '.join(standardized)

class DutchDateParser:
    """Handles Dutch date formats and conversions"""

    DUTCH_MONTHS = {
        'januari': 'JAN', 'februari': 'FEB', 'maart': 'MAR', 'april': 'APR',
        'mei': 'MAY', 'juni': 'JUN', 'juli': 'JUL', 'augustus': 'AUG',
        'september': 'SEP', 'oktober': 'OCT', 'november': 'NOV', 'december': 'DEC',
        'jan': 'JAN', 'feb': 'FEB', 'mrt': 'MAR', 'apr': 'APR',
        'jun': 'JUN', 'jul': 'JUL', 'aug': 'AUG',
        'sep': 'SEP', 'okt': 'OCT', 'nov': 'NOV', 'dec': 'DEC'
    }

    @classmethod
    def parse_dutch_date(cls, date_str: str) -> str:
        """
        Parse Dutch date formats and convert to GEDCOM format (DD MMM YYYY)
        """
        if not date_str:
            return ""

        date_str = date_str.strip()

        # Dutch month names
        for dutch_month, english_abbr in cls.DUTCH_MONTHS.items():
            pattern = rf'(\d{{1,2}})\s+{dutch_month}\s+(\d{{4}})'
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                year = match.group(2)
                return f"{day:02d} {english_abbr} {year}"

        # DD.MM.YYYY format (common in Dutch records)
        dd_mm_yyyy = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
        if dd_mm_yyyy:
            day, month, year = dd_mm_yyyy.groups()
            try:
                day_int = int(day)
                month_int = int(month)
                if 1 <= month_int <= 12:
                    month_names = ['', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                                 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
                    return f"{day_int:02d} {month_names[month_int]} {year}"
            except ValueError:
                pass

        # Just year
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            return year_match.group(1)

        return date_str[:20]  # Return original, truncated for GEDCOM

    @classmethod
    def extract_dates_from_text(cls, text: str) -> list[str]:
        """Extract all potential dates from Dutch text"""
        dates = []

        # Dutch date patterns
        patterns = [
            r'\d{1,2}\s+(?:januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\s+\d{4}',
            r'\d{1,2}\.\d{1,2}\.\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\b\d{4}\b'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append(match.group().strip())

        return dates

class DutchPlaceParser:
    """Handles Dutch place names and geographic conventions"""

    # Common Dutch place name patterns
    PLACE_INDICATORS = [
        'te', 'in', 'van', 'bij', 'nabij', 'gemeente', 'stad', 'dorp'
    ]

    @classmethod
    def parse_place_string(cls, place_str: str) -> dict:
        """
        Parse Dutch place string into components
        Returns dict with: place, municipality, province, country
        """
        if not place_str:
            return {}

        place_str = place_str.strip()

        # Remove common prefixes
        for indicator in cls.PLACE_INDICATORS:
            pattern = rf'\b{indicator}\s+'
            place_str = re.sub(pattern, '', place_str, flags=re.IGNORECASE).strip()

        # Split by commas (common format: "Place, Municipality, Province")
        parts = [p.strip() for p in place_str.split(',')]

        result = {
            'place': parts[0] if parts else place_str,
            'municipality': parts[1] if len(parts) > 1 else '',
            'province': parts[2] if len(parts) > 2 else '',
            'country': parts[3] if len(parts) > 3 else 'Nederland'
        }

        return result

    @classmethod
    def standardize_place_name(cls, place_name: str) -> str:
        """Standardize Dutch place name capitalization"""
        if not place_name:
            return ""

        # Capitalize each word, but handle special cases
        words = place_name.split()
        standardized = []

        for word in words:
            # Don't capitalize prepositions unless they're the first word
            if word.lower() in ['aan', 'bij', 'in', 'op', 'te', 'van'] and standardized:
                standardized.append(word.lower())
            else:
                standardized.append(word.capitalize())

        return ' '.join(standardized)

    @classmethod
    def is_dutch_place(cls, place_name: str) -> bool:
        """Check if a place name appears to be Dutch"""
        if not place_name:
            return False

        place_lower = place_name.lower()

        # Check for Dutch place indicators
        dutch_indicators = [
            'nederland', 'holland', 'amsterdam', 'rotterdam', 'den haag',
            'utrecht', 'groningen', 'friesland', 'gelderland', 'limburg',
            'brabant', 'zeeland', 'overijssel', 'drenthe'
        ]

        for indicator in dutch_indicators:
            if indicator in place_lower:
                return True

        # Check for Dutch place patterns (ending in -en, -um, etc.)
        dutch_endings = ['en', 'um', 'ijk', 'wijk', 'dijk', 'dam', 'berg', 'huis']
        for ending in dutch_endings:
            if place_lower.endswith(ending):
                return True

        return False
