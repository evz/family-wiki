"""
Tests for Dutch genealogy utilities
"""


from web_app.shared.dutch_utils import DutchDateParser, DutchNameParser, DutchPlaceParser


class TestDutchNameParser:
    """Test Dutch name parsing functionality"""

    def test_parse_full_name_empty(self):
        """Test parsing empty name"""
        result = DutchNameParser.parse_full_name("")
        assert result == ("", "", "")

    def test_parse_full_name_simple(self):
        """Test parsing simple name without particles"""
        result = DutchNameParser.parse_full_name("Jan Jansen")
        assert result == ("Jan", "", "Jansen")

    def test_parse_full_name_with_particles(self):
        """Test parsing name with particles"""
        result = DutchNameParser.parse_full_name("Jan van der Berg")
        assert result == ("Jan", "van der", "Berg")

    def test_parse_full_name_gedcom_format(self):
        """Test parsing GEDCOM format name"""
        result = DutchNameParser.parse_full_name("Jan /van der Berg/")
        assert result == ("Jan", "van der", "Berg")

    def test_parse_full_name_multiple_given_names(self):
        """Test parsing name with multiple given names"""
        result = DutchNameParser.parse_full_name("Jan Pieter van der Berg")
        assert result == ("Jan Pieter", "van der", "Berg")

    def test_parse_full_name_particles_in_given(self):
        """Test parsing name with particles in given name part"""
        result = DutchNameParser.parse_full_name("Jan van Pieter Berg")
        # Should extract particles from given names
        given, particle, surname = result
        assert given == "Jan"
        assert particle == "van Pieter"
        assert surname == "Berg"

    def test_extract_particles_basic(self):
        """Test basic particle extraction"""
        result = DutchNameParser._extract_particles_from_given("Jan van Pieter")
        assert result == ("Jan", "van")

    def test_extract_particles_no_particles(self):
        """Test extraction when no particles present"""
        result = DutchNameParser._extract_particles_from_given("Jan Pieter")
        assert result == ("Jan Pieter", "")

    def test_extract_particles_multiple_particles(self):
        """Test extraction with multiple particles"""
        result = DutchNameParser._extract_particles_from_given("Jan van der Meer")
        assert result == ("Jan", "van der")

    def test_detect_gender_male(self):
        """Test male gender detection"""
        assert DutchNameParser.detect_gender("Jan") == "M"
        assert DutchNameParser.detect_gender("Johannes") == "M"
        assert DutchNameParser.detect_gender("Pieter") == "M"

    def test_detect_gender_female(self):
        """Test female gender detection"""
        assert DutchNameParser.detect_gender("Maria") == "F"
        assert DutchNameParser.detect_gender("Anna") == "F"
        assert DutchNameParser.detect_gender("Elisabeth") == "F"

    def test_detect_gender_unknown(self):
        """Test unknown gender detection"""
        assert DutchNameParser.detect_gender("Unknown") is None
        assert DutchNameParser.detect_gender("") is None

    def test_detect_gender_case_insensitive(self):
        """Test case insensitive gender detection"""
        assert DutchNameParser.detect_gender("JOHANNES") == "M"
        assert DutchNameParser.detect_gender("maria") == "F"

    def test_standardize_name(self):
        """Test name standardization"""
        assert DutchNameParser.standardize_name("jan pieter") == "Jan Pieter"
        assert DutchNameParser.standardize_name("jan van der berg") == "Jan van der Berg"
        assert DutchNameParser.standardize_name("  jan   pieter  ") == "Jan Pieter"


class TestDutchDateParser:
    """Test Dutch date parsing functionality"""

    def test_parse_dutch_date_empty(self):
        """Test parsing empty date"""
        result = DutchDateParser.parse_dutch_date("")
        assert result == ""

    def test_parse_dutch_date_standard_format(self):
        """Test parsing standard date format"""
        result = DutchDateParser.parse_dutch_date("1 januari 1800")
        assert result == "01 JAN 1800"

    def test_parse_dutch_date_numeric_format(self):
        """Test parsing numeric date format"""
        result = DutchDateParser.parse_dutch_date("01.01.1800")
        assert result == "01 JAN 1800"

    def test_parse_dutch_date_year_only(self):
        """Test parsing year only"""
        result = DutchDateParser.parse_dutch_date("1800")
        assert result == "1800"

    def test_parse_dutch_date_invalid(self):
        """Test parsing invalid date"""
        result = DutchDateParser.parse_dutch_date("invalid date")
        assert result == "invalid date"

    def test_extract_dates_from_text(self):
        """Test extracting dates from text"""
        text = "Hij werd geboren op 1 januari 1800 en overleed op 31.12.1870"
        result = DutchDateParser.extract_dates_from_text(text)
        assert len(result) >= 2
        assert "1 januari 1800" in result
        assert "31.12.1870" in result


class TestDutchPlaceParser:
    """Test Dutch place name parsing"""

    def test_parse_place_string_empty(self):
        """Test parsing empty place string"""
        result = DutchPlaceParser.parse_place_string("")
        assert result == {}

    def test_parse_place_string_simple(self):
        """Test parsing simple place name"""
        result = DutchPlaceParser.parse_place_string("Amsterdam")
        assert result['place'] == "Amsterdam"
        assert result['country'] == "Nederland"

    def test_parse_place_string_with_province(self):
        """Test parsing place with province"""
        result = DutchPlaceParser.parse_place_string("Amsterdam, Noord-Holland")
        assert result['place'] == "Amsterdam"
        assert result['municipality'] == "Noord-Holland"
        assert result['country'] == "Nederland"

    def test_parse_place_string_full_format(self):
        """Test parsing full place format"""
        result = DutchPlaceParser.parse_place_string("Amsterdam, Amsterdam, Noord-Holland, Nederland")
        assert result['place'] == "Amsterdam"
        assert result['municipality'] == "Amsterdam"
        assert result['province'] == "Noord-Holland"
        assert result['country'] == "Nederland"

    def test_parse_place_string_with_indicators(self):
        """Test parsing place with indicators"""
        result = DutchPlaceParser.parse_place_string("te Amsterdam")
        assert result['place'] == "Amsterdam"

    def test_standardize_place_name_empty(self):
        """Test standardizing empty place name"""
        result = DutchPlaceParser.standardize_place_name("")
        assert result == ""

    def test_standardize_place_name_basic(self):
        """Test basic place name standardization"""
        result = DutchPlaceParser.standardize_place_name("amsterdam")
        assert result == "Amsterdam"

    def test_standardize_place_name_with_prepositions(self):
        """Test place name with prepositions"""
        result = DutchPlaceParser.standardize_place_name("bergen op zoom")
        assert result == "Bergen op Zoom"

    def test_is_dutch_place(self):
        """Test Dutch place detection"""
        assert DutchPlaceParser.is_dutch_place("Amsterdam") is True
        assert DutchPlaceParser.is_dutch_place("London") is False
