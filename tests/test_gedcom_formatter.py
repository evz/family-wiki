"""
Tests for GEDCOM formatter - formatting genealogy data to GEDCOM format
"""
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from web_app.shared.gedcom_formatter import GEDCOMFileWriter, GEDCOMFormatter


class TestGEDCOMFormatter:
    """Test GEDCOM formatter functionality"""

    @pytest.fixture
    def formatter(self):
        """GEDCOM formatter instance"""
        return GEDCOMFormatter()

    @pytest.fixture
    def sample_person(self):
        """Sample person for testing"""
        person = Mock()
        person.given_names = "Johannes"
        person.surname = "Smith"
        person.tussenvoegsel = "van"
        person.sex = "M"
        person.birth_date = "1850"
        person.birth_place = "Amsterdam"
        person.baptism_date = "1850-02-15"
        person.baptism_place = "Amsterdam, NH"
        person.death_date = "1920"
        person.death_place = "Utrecht"
        person.notes = "Some notes about the person"
        person.occupations = ["farmer", "baker"]
        return person

    @pytest.fixture
    def minimal_person(self):
        """Minimal person with only required fields"""
        person = Mock()
        person.given_names = "Johannes"
        person.surname = None
        person.tussenvoegsel = None
        person.sex = None
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = None
        person.occupations = []
        return person

    @pytest.fixture
    def sample_family(self):
        """Sample family for testing"""
        family = Mock()
        family.husband_id = "0001"
        family.wife_id = "0002"
        family.children_ids = ["0003", "0004"]
        family.marriage_date = "1875-06-15"
        family.marriage_place = "Amsterdam"
        return family

    def test_init(self, formatter):
        """Test formatter initialization"""
        assert formatter.person_counter == 1
        assert formatter.family_counter == 1
        assert formatter.source_counter == 1

    def test_format_header(self, formatter):
        """Test GEDCOM header formatting"""
        with patch('web_app.shared.gedcom_formatter.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 12, 25, 10, 30, 45)
            header = formatter._format_header()

        expected_lines = [
            "0 HEAD",
            "1 SOUR VanBulhuisExtractor",
            "2 VERS 1.0",
            "2 NAME Van Bulhuis Family Book Extractor",
            "1 DATE 25 DEC 2023",
            "1 FILE family_tree.ged",
            "1 GEDC",
            "2 VERS 5.5.1",
            "2 FORM LINEAGE-LINKED",
            "1 CHAR UTF-8",
            "1 LANG English"
        ]

        assert header == expected_lines

    def test_format_trailer(self, formatter):
        """Test GEDCOM trailer formatting"""
        trailer = formatter._format_trailer()
        assert trailer == ["0 TRLR"]

    def test_format_individual_full_data(self, formatter, sample_person):
        """Test formatting individual with full data"""
        with patch('web_app.shared.dutch_utils.DutchNameParser'):
            lines = formatter._format_individual(sample_person)

        assert lines[0] == "0 @I0001@ INDI"
        assert "1 NAME Johannes /van Smith/" in lines
        assert "2 GIVN Johannes" in lines
        assert "2 SURN Smith" in lines
        assert "2 NPFX van" in lines
        assert "1 SEX M" in lines
        assert "1 BIRT" in lines
        assert "2 DATE 1850" in lines
        assert "2 PLAC Amsterdam" in lines
        assert "1 BAPM" in lines
        assert "2 DATE 1850-02-15" in lines
        assert "2 PLAC Amsterdam, NH" in lines
        assert "1 DEAT" in lines
        assert "2 DATE 1920" in lines
        assert "2 PLAC Utrecht" in lines
        assert "1 OCCU farmer" in lines
        assert "1 OCCU baker" in lines
        assert "1 NOTE Some notes about the person" in lines

    def test_format_individual_minimal_data(self, formatter, minimal_person):
        """Test formatting individual with minimal data"""
        with patch('web_app.shared.dutch_utils.DutchNameParser') as mock_parser:
            mock_parser.detect_gender.return_value = None  # No gender detected
            lines = formatter._format_individual(minimal_person)

        assert lines[0] == "0 @I0001@ INDI"
        assert "1 NAME Johannes" in lines
        assert "2 GIVN Johannes" in lines
        # Should not contain fields for missing data
        assert not any("SURN" in line for line in lines)
        assert not any("NPFX" in line for line in lines)
        assert not any("SEX" in line for line in lines)
        assert not any("BIRT" in line for line in lines)
        assert not any("BAPM" in line for line in lines)
        assert not any("DEAT" in line for line in lines)
        assert not any("OCCU" in line for line in lines)
        assert not any("NOTE" in line for line in lines)

    def test_format_individual_no_names(self, formatter):
        """Test formatting individual with no names"""
        person = Mock()
        person.given_names = None
        person.surname = None
        person.tussenvoegsel = None
        person.sex = "M"
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = None
        person.occupations = []

        lines = formatter._format_individual(person)

        assert lines[0] == "0 @I0001@ INDI"
        assert "1 SEX M" in lines
        # Should not contain name lines
        assert not any("NAME" in line for line in lines)
        assert not any("GIVN" in line for line in lines)

    def test_format_individual_gender_detection(self, formatter):
        """Test gender detection for individuals"""
        person = Mock()
        person.given_names = "Johannes"
        person.surname = "Smith"
        person.tussenvoegsel = None
        person.sex = None  # No sex provided
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = None
        person.occupations = []

        with patch('web_app.shared.dutch_utils.DutchNameParser') as mock_parser:
            mock_parser.detect_gender.return_value = "M"
            lines = formatter._format_individual(person)

        assert "1 SEX M" in lines
        mock_parser.detect_gender.assert_called_once_with("Johannes")

    def test_format_individual_gender_detection_no_result(self, formatter):
        """Test gender detection when no gender detected"""
        person = Mock()
        person.given_names = "Johannes"
        person.surname = "Smith"
        person.tussenvoegsel = None
        person.sex = None
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = None
        person.occupations = []

        with patch('web_app.shared.dutch_utils.DutchNameParser') as mock_parser:
            mock_parser.detect_gender.return_value = None
            lines = formatter._format_individual(person)

        # Should not contain SEX line when gender detection fails
        assert not any("SEX" in line for line in lines)

    def test_format_individual_surname_only(self, formatter):
        """Test formatting individual with surname only"""
        person = Mock()
        person.given_names = None
        person.surname = "Smith"
        person.tussenvoegsel = "van"
        person.sex = None
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = None
        person.occupations = []

        with patch('web_app.shared.dutch_utils.DutchNameParser'):
            lines = formatter._format_individual(person)

        assert "1 NAME /van Smith/" in lines
        assert "2 SURN Smith" in lines
        assert "2 NPFX van" in lines
        # Should not contain given name
        assert not any("GIVN" in line for line in lines)

    def test_format_individual_occupation_filtering(self, formatter):
        """Test that empty occupations are filtered out"""
        person = Mock()
        person.given_names = "Johannes"
        person.surname = "Smith"
        person.tussenvoegsel = None
        person.sex = None
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = None
        person.occupations = ["farmer", "", "  ", "baker"]  # Include empty/whitespace

        with patch('web_app.shared.dutch_utils.DutchNameParser'):
            lines = formatter._format_individual(person)

        occupation_lines = [line for line in lines if "OCCU" in line]
        assert len(occupation_lines) == 2
        assert "1 OCCU farmer" in lines
        assert "1 OCCU baker" in lines

    def test_format_individual_person_counter_increment(self, formatter):
        """Test that person counter increments correctly"""
        person1 = Mock()
        person1.given_names = "Johannes"
        person1.surname = None
        person1.tussenvoegsel = None
        person1.sex = None
        person1.birth_date = None
        person1.birth_place = None
        person1.baptism_date = None
        person1.baptism_place = None
        person1.death_date = None
        person1.death_place = None
        person1.notes = None
        person1.occupations = []

        person2 = Mock()
        person2.given_names = "Maria"
        person2.surname = None
        person2.tussenvoegsel = None
        person2.sex = None
        person2.birth_date = None
        person2.birth_place = None
        person2.baptism_date = None
        person2.baptism_place = None
        person2.death_date = None
        person2.death_place = None
        person2.notes = None
        person2.occupations = []

        with patch('web_app.shared.dutch_utils.DutchNameParser'):
            lines1 = formatter._format_individual(person1)
            lines2 = formatter._format_individual(person2)

        assert lines1[0] == "0 @I0001@ INDI"
        assert lines2[0] == "0 @I0002@ INDI"
        assert formatter.person_counter == 3

    def test_format_family_full_data(self, formatter, sample_family):
        """Test formatting family with full data"""
        lines = formatter._format_family(sample_family)

        assert lines[0] == "0 @F0001@ FAM"
        assert "1 HUSB @I0001@" in lines
        assert "1 WIFE @I0002@" in lines
        assert "1 CHIL @I0003@" in lines
        assert "1 CHIL @I0004@" in lines
        assert "1 MARR" in lines
        assert "2 DATE 1875-06-15" in lines
        assert "2 PLAC Amsterdam" in lines

    def test_format_family_minimal_data(self, formatter):
        """Test formatting family with minimal data"""
        family = Mock()
        family.husband_id = None
        family.wife_id = None
        family.children_ids = []
        # Explicitly set these to None to prevent Mock auto-creation
        del family.marriage_date
        del family.marriage_place

        lines = formatter._format_family(family)

        assert lines[0] == "0 @F0001@ FAM"
        # Should only contain family header
        assert len(lines) == 1

    def test_format_family_marriage_only(self, formatter):
        """Test formatting family with marriage data only"""
        family = Mock()
        family.husband_id = None
        family.wife_id = None
        family.children_ids = []
        family.marriage_date = "1875"
        family.marriage_place = "Amsterdam"

        lines = formatter._format_family(family)

        assert lines[0] == "0 @F0001@ FAM"
        assert "1 MARR" in lines
        assert "2 DATE 1875" in lines
        assert "2 PLAC Amsterdam" in lines

    def test_format_family_counter_increment(self, formatter):
        """Test that family counter increments correctly"""
        family1 = Mock()
        family1.husband_id = None
        family1.wife_id = None
        family1.children_ids = []
        del family1.marriage_date
        del family1.marriage_place

        family2 = Mock()
        family2.husband_id = None
        family2.wife_id = None
        family2.children_ids = []
        del family2.marriage_date
        del family2.marriage_place

        lines1 = formatter._format_family(family1)
        lines2 = formatter._format_family(family2)

        assert lines1[0] == "0 @F0001@ FAM"
        assert lines2[0] == "0 @F0002@ FAM"
        assert formatter.family_counter == 3

    def test_split_note_short(self, formatter):
        """Test splitting short note"""
        note = "Short note"
        result = formatter._split_note(note)
        assert result == ["Short note"]

    def test_split_note_long(self, formatter):
        """Test splitting long note"""
        note = "This is a very long note that should be split into multiple lines because it exceeds the maximum length"
        result = formatter._split_note(note, max_length=30)

        assert len(result) > 1
        for line in result:
            assert len(line) <= 30
        # Verify the content is preserved
        reconstructed = " ".join(result)
        assert reconstructed == note

    def test_split_note_exact_length(self, formatter):
        """Test splitting note that is exactly max length"""
        note = "This note is exactly thirty characters long."  # 45 chars
        result = formatter._split_note(note, max_length=45)
        assert result == [note]

    def test_split_note_word_boundary(self, formatter):
        """Test that note splitting respects word boundaries"""
        note = "word1 word2 word3 word4 word5"
        result = formatter._split_note(note, max_length=15)

        # Each line should contain complete words
        for line in result:
            assert not line.startswith(" ")
            assert not line.endswith(" ")

    def test_format_gedcom_people_only(self, formatter, sample_person):
        """Test formatting GEDCOM with people only"""
        with patch('web_app.shared.gedcom_formatter.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 12, 25)
            with patch('web_app.shared.dutch_utils.DutchNameParser'):
                lines = formatter.format_gedcom([sample_person])

        # Should contain header, person, and trailer
        assert lines[0] == "0 HEAD"
        assert "0 @I0001@ INDI" in lines
        assert lines[-1] == "0 TRLR"

    def test_format_gedcom_people_and_families(self, formatter, sample_person, sample_family):
        """Test formatting GEDCOM with people and families"""
        with patch('web_app.shared.gedcom_formatter.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 12, 25)
            with patch('web_app.shared.dutch_utils.DutchNameParser'):
                lines = formatter.format_gedcom([sample_person], [sample_family])

        # Should contain header, person, family, and trailer
        assert lines[0] == "0 HEAD"
        assert "0 @I0001@ INDI" in lines
        assert "0 @F0001@ FAM" in lines
        assert lines[-1] == "0 TRLR"

    def test_format_gedcom_empty_lists(self, formatter):
        """Test formatting GEDCOM with empty lists"""
        with patch('web_app.shared.gedcom_formatter.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 12, 25)
            lines = formatter.format_gedcom([], [])

        # Should contain only header and trailer
        assert lines[0] == "0 HEAD"
        assert lines[-1] == "0 TRLR"
        # Should not contain any individual or family records
        assert not any("INDI" in line for line in lines)
        assert not any("FAM" in line for line in lines)

    def test_format_individual_long_note(self, formatter):
        """Test formatting individual with long note"""
        person = Mock()
        person.given_names = "Johannes"
        person.surname = None
        person.tussenvoegsel = None
        person.sex = None
        person.birth_date = None
        person.birth_place = None
        person.baptism_date = None
        person.baptism_place = None
        person.death_date = None
        person.death_place = None
        person.notes = "This is a very long note that should be split into multiple lines when formatted in GEDCOM format"
        person.occupations = []

        with patch('web_app.shared.dutch_utils.DutchNameParser'):
            lines = formatter._format_individual(person)

        note_lines = [line for line in lines if "NOTE" in line or "CONT" in line]
        assert len(note_lines) > 1
        assert note_lines[0].startswith("1 NOTE")
        for line in note_lines[1:]:
            assert line.startswith("2 CONT")


class TestGEDCOMFileWriter:
    """Test GEDCOM file writer functionality"""

    def test_write_gedcom_file(self):
        """Test writing GEDCOM lines to file"""
        lines = ["0 HEAD", "1 SOUR Test", "0 TRLR"]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged') as tmp_file:
            temp_path = tmp_file.name

        try:
            GEDCOMFileWriter.write_gedcom_file(lines, temp_path)

            # Verify file contents
            with open(temp_path, encoding='utf-8') as f:
                content = f.read()
                assert content == "0 HEAD\n1 SOUR Test\n0 TRLR"
        finally:
            Path(temp_path).unlink()

    def test_read_gedcom_file(self):
        """Test reading GEDCOM lines from file"""
        content = "0 HEAD\n1 SOUR Test\n0 TRLR"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged') as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name

        try:
            lines = GEDCOMFileWriter.read_gedcom_file(temp_path)
            assert lines == ["0 HEAD", "1 SOUR Test", "0 TRLR"]
        finally:
            Path(temp_path).unlink()

    def test_write_read_roundtrip(self):
        """Test writing and reading GEDCOM file roundtrip"""
        original_lines = [
            "0 HEAD",
            "1 SOUR VanBulhuisExtractor",
            "0 @I0001@ INDI",
            "1 NAME Johannes /Smith/",
            "0 TRLR"
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged') as tmp_file:
            temp_path = tmp_file.name

        try:
            # Write and read back
            GEDCOMFileWriter.write_gedcom_file(original_lines, temp_path)
            read_lines = GEDCOMFileWriter.read_gedcom_file(temp_path)

            assert read_lines == original_lines
        finally:
            Path(temp_path).unlink()

    def test_write_gedcom_file_utf8_encoding(self):
        """Test writing GEDCOM file with UTF-8 characters"""
        lines = ["0 HEAD", "1 NAME João /da Silva/", "0 TRLR"]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged') as tmp_file:
            temp_path = tmp_file.name

        try:
            GEDCOMFileWriter.write_gedcom_file(lines, temp_path)

            # Verify UTF-8 encoding is preserved
            with open(temp_path, encoding='utf-8') as f:
                content = f.read()
                assert "João" in content
        finally:
            Path(temp_path).unlink()

    def test_read_gedcom_file_utf8_encoding(self):
        """Test reading GEDCOM file with UTF-8 characters"""
        content = "0 HEAD\n1 NAME João /da Silva/\n0 TRLR"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged', encoding='utf-8') as tmp_file:
            tmp_file.write(content)
            temp_path = tmp_file.name

        try:
            lines = GEDCOMFileWriter.read_gedcom_file(temp_path)
            assert lines == ["0 HEAD", "1 NAME João /da Silva/", "0 TRLR"]
            assert "João" in lines[1]
        finally:
            Path(temp_path).unlink()
