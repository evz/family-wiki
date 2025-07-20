"""
Tests for Dutch genealogy parser
"""

from web_app.shared.dutch_genealogy_parser import DutchGenealogyParser


class TestDutchGenealogyParser:
    """Test the Dutch genealogy parser"""

    def test_parse_dutch_name_single_name(self):
        """Test parsing single name"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Johannes")
        assert given == "Johannes"
        assert tussenvoegsel == ""
        assert surname == ""

    def test_parse_dutch_name_two_parts(self):
        """Test parsing two-part name"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Johannes Jansen")
        assert given == "Johannes"
        assert tussenvoegsel == ""
        assert surname == "Jansen"

    def test_parse_dutch_name_with_simple_tussenvoegsel(self):
        """Test parsing name with simple tussenvoegsel"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Johannes van Berg")
        assert given == "Johannes"
        assert tussenvoegsel == "van"
        assert surname == "Berg"

    def test_parse_dutch_name_with_compound_tussenvoegsel(self):
        """Test parsing name with compound tussenvoegsel"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Johannes van der Berg")
        assert given == "Johannes"
        assert tussenvoegsel == "van der"
        assert surname == "Berg"

    def test_parse_dutch_name_with_multiple_tussenvoegsel(self):
        """Test parsing name with multiple tussenvoegsel"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Johannes van de Berg")
        assert given == "Johannes"
        assert tussenvoegsel == "van de"
        assert surname == "Berg"

    def test_parse_dutch_name_complex_case(self):
        """Test parsing complex Dutch name"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Jan Willem van der Berg")
        assert given == "Jan Willem"  # Multiple given names
        assert tussenvoegsel == "van der"
        assert surname == "Berg"

    def test_parse_dutch_name_empty_string(self):
        """Test parsing empty string"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("")
        assert given == ""
        assert tussenvoegsel == ""
        assert surname == ""

    def test_parse_dutch_name_none(self):
        """Test parsing None"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name(None)
        assert given == ""
        assert tussenvoegsel == ""
        assert surname == ""

    def test_parse_dutch_name_whitespace(self):
        """Test parsing whitespace-only string"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("   ")
        assert given == ""
        assert tussenvoegsel == ""
        assert surname == ""

    def test_parse_dutch_name_with_de(self):
        """Test parsing name with 'de' tussenvoegsel"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Maria de Jong")
        assert given == "Maria"
        assert tussenvoegsel == "de"
        assert surname == "Jong"

    def test_parse_dutch_name_with_multiple_surnames(self):
        """Test parsing name with multiple surname parts"""
        given, tussenvoegsel, surname = DutchGenealogyParser.parse_dutch_name("Johannes van Berg Smith")
        assert given == "Johannes"
        assert tussenvoegsel == "van"
        assert surname == "Berg Smith"

    def test_parse_dutch_date_dd_mm_yyyy_dash(self):
        """Test parsing DD-MM-YYYY format"""
        result = DutchGenealogyParser.parse_dutch_date("15-06-1850")
        assert result == "1850-06-15"

    def test_parse_dutch_date_dd_mm_yyyy_slash(self):
        """Test parsing DD/MM/YYYY format"""
        result = DutchGenealogyParser.parse_dutch_date("15/06/1850")
        assert result == "1850-06-15"

    def test_parse_dutch_date_dd_mm_yyyy_dot(self):
        """Test parsing DD.MM.YYYY format"""
        result = DutchGenealogyParser.parse_dutch_date("15.06.1850")
        assert result == "1850-06-15"

    def test_parse_dutch_date_yyyy_mm_dd(self):
        """Test parsing YYYY-MM-DD format"""
        result = DutchGenealogyParser.parse_dutch_date("1850-06-15")
        assert result == "1850-06-15"

    def test_parse_dutch_date_with_dutch_month(self):
        """Test parsing date with Dutch month name"""
        result = DutchGenealogyParser.parse_dutch_date("15 juni 1850")
        assert result == "1850-06-15"

    def test_parse_dutch_date_with_abbreviated_month(self):
        """Test parsing date with abbreviated Dutch month"""
        result = DutchGenealogyParser.parse_dutch_date("15 jun 1850")
        assert result == "1850-06-15"

    def test_parse_dutch_date_empty_string(self):
        """Test parsing empty date string"""
        result = DutchGenealogyParser.parse_dutch_date("")
        assert result == ""

    def test_parse_dutch_date_none(self):
        """Test parsing None date"""
        result = DutchGenealogyParser.parse_dutch_date(None)
        assert result == ""

    def test_parse_dutch_date_invalid_format(self):
        """Test parsing invalid date format"""
        result = DutchGenealogyParser.parse_dutch_date("invalid date")
        assert result == "invalid date"  # Returns as-is

    def test_parse_dutch_date_unknown_month(self):
        """Test parsing date with unknown month"""
        result = DutchGenealogyParser.parse_dutch_date("15 unknownmonth 1850")
        assert result == "15 unknownmonth 1850"  # Returns as-is

    def test_normalize_place_name_basic(self):
        """Test basic place name normalization"""
        result = DutchGenealogyParser.normalize_place_name("amsterdam")
        assert result == "Amsterdam"

    def test_normalize_place_name_with_prefix(self):
        """Test place name with Dutch prefix"""
        result = DutchGenealogyParser.normalize_place_name("te Amsterdam")
        assert result == "Amsterdam"

    def test_normalize_place_name_with_suffix(self):
        """Test place name with Dutch suffix"""
        result = DutchGenealogyParser.normalize_place_name("Amsterdam Nederland")
        assert result == "Amsterdam"

    def test_normalize_place_name_multiple_words(self):
        """Test multi-word place name"""
        result = DutchGenealogyParser.normalize_place_name("den haag")
        assert result == "Den Haag"

    def test_normalize_place_name_empty_string(self):
        """Test empty place name"""
        result = DutchGenealogyParser.normalize_place_name("")
        assert result == ""

    def test_normalize_place_name_none(self):
        """Test None place name"""
        result = DutchGenealogyParser.normalize_place_name(None)
        assert result == ""

    def test_extract_generation_info_basic(self):
        """Test basic generation extraction"""
        result = DutchGenealogyParser.extract_generation_info("3e generatie")
        assert result == 3

    def test_extract_generation_info_without_suffix(self):
        """Test generation extraction without suffix"""
        result = DutchGenealogyParser.extract_generation_info("generatie 5")
        assert result == 5

    def test_extract_generation_info_abbreviated(self):
        """Test abbreviated generation extraction"""
        result = DutchGenealogyParser.extract_generation_info("gen. 2")
        assert result == 2

    def test_extract_generation_info_short_format(self):
        """Test short generation format"""
        result = DutchGenealogyParser.extract_generation_info("4e gen")
        assert result == 4

    def test_extract_generation_info_no_match(self):
        """Test generation extraction with no match"""
        result = DutchGenealogyParser.extract_generation_info("some text")
        assert result is None

    def test_extract_generation_info_empty_string(self):
        """Test generation extraction with empty string"""
        result = DutchGenealogyParser.extract_generation_info("")
        assert result is None

    def test_extract_generation_info_none(self):
        """Test generation extraction with None"""
        result = DutchGenealogyParser.extract_generation_info(None)
        assert result is None

    def test_parse_family_relationships_children_indicator(self):
        """Test parsing children relationships"""
        result = DutchGenealogyParser.parse_family_relationships("Kinderen van Johannes")
        assert 'kinderen van' in result['children']

    def test_parse_family_relationships_marriage_indicator(self):
        """Test parsing marriage relationships"""
        result = DutchGenealogyParser.parse_family_relationships("gehuwd met Maria")
        assert 'gehuwd met' in result['spouses']

    def test_parse_family_relationships_multiple_indicators(self):
        """Test parsing multiple relationship indicators"""
        text = "Johannes gehuwd met Maria, kinderen van deze verbintenis"
        result = DutchGenealogyParser.parse_family_relationships(text)
        assert 'gehuwd met' in result['spouses']
        assert 'kinderen van' in result['children']

    def test_parse_family_relationships_empty_string(self):
        """Test parsing empty relationship string"""
        result = DutchGenealogyParser.parse_family_relationships("")
        assert result['children'] == []
        assert result['spouses'] == []

    def test_parse_family_relationships_none(self):
        """Test parsing None relationship text"""
        result = DutchGenealogyParser.parse_family_relationships(None)
        assert result['children'] == []
        assert result['spouses'] == []

    def test_calculate_summary_statistics_basic(self):
        """Test basic summary statistics calculation"""
        families = [{
            'parents': {'father': {'name': 'John'}, 'mother': {'name': 'Jane'}},
            'children': [{'name': 'Child1'}, {'name': 'Child2'}],
            'confidence_score': 0.9
        }]
        isolated = [{'name': 'Bob', 'confidence_score': 0.8}]

        stats = DutchGenealogyParser.calculate_summary_statistics(families, isolated)

        assert stats['total_families'] == 1
        assert stats['total_isolated_individuals'] == 1
        assert stats['total_people'] == 5  # 2 parents + 2 children + 1 isolated
        assert stats['total_parents'] == 2
        assert stats['total_children'] == 2
        assert abs(stats['average_confidence'] - 0.85) < 0.001  # (0.9 + 0.8) / 2

    def test_calculate_summary_statistics_empty_data(self):
        """Test summary statistics with empty data"""
        stats = DutchGenealogyParser.calculate_summary_statistics([], [])

        assert stats['total_families'] == 0
        assert stats['total_isolated_individuals'] == 0
        assert stats['total_people'] == 0
        assert stats['total_parents'] == 0
        assert stats['total_children'] == 0
        assert stats['average_confidence'] == 0.0

    def test_calculate_summary_statistics_with_generations(self):
        """Test summary statistics with generation information"""
        families = [{
            'parents': {'father': {'name': 'John'}},
            'children': [{'name': 'Child1'}],
            'generation': '3e generatie'
        }]
        isolated = [{'name': 'Bob', 'generation': 'generatie 5'}]

        stats = DutchGenealogyParser.calculate_summary_statistics(families, isolated)

        assert stats['generations_count'] == 2  # Generations 3 and 5

    def test_calculate_summary_statistics_no_parents(self):
        """Test statistics with family without parents"""
        families = [{
            'children': [{'name': 'Child1'}]
        }]

        stats = DutchGenealogyParser.calculate_summary_statistics(families, [])

        assert stats['total_parents'] == 0
        assert stats['total_children'] == 1
        assert stats['total_people'] == 1

    def test_calculate_summary_statistics_only_father(self):
        """Test statistics with only father"""
        families = [{
            'parents': {'father': {'name': 'John'}},
            'children': [{'name': 'Child1'}]
        }]

        stats = DutchGenealogyParser.calculate_summary_statistics(families, [])

        assert stats['total_parents'] == 1
        assert stats['total_children'] == 1
        assert stats['total_people'] == 2

    def test_calculate_summary_statistics_only_mother(self):
        """Test statistics with only mother"""
        families = [{
            'parents': {'mother': {'name': 'Jane'}},
            'children': [{'name': 'Child1'}]
        }]

        stats = DutchGenealogyParser.calculate_summary_statistics(families, [])

        assert stats['total_parents'] == 1
        assert stats['total_children'] == 1
        assert stats['total_people'] == 2
