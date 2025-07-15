"""
Tests for GEDCOM formatter (separated from file I/O)
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from web_app.shared.gedcom_formatter import GEDCOMFileWriter, GEDCOMFormatter
from web_app.shared.models import Family, Person


class TestGEDCOMFormatter:
    """Test GEDCOM formatting without file I/O"""

    def test_format_header(self):
        """Test GEDCOM header formatting"""
        formatter = GEDCOMFormatter()

        with patch('web_app.shared.gedcom_formatter.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "01 JAN 2024"

            header = formatter._format_header()

        assert header[0] == "0 HEAD"
        assert "1 SOUR VanBulhuisExtractor" in header
        assert "1 DATE 01 JAN 2024" in header
        assert "2 VERS 5.5.1" in header
        assert "1 CHAR UTF-8" in header

    def test_format_trailer(self):
        """Test GEDCOM trailer formatting"""
        formatter = GEDCOMFormatter()
        trailer = formatter._format_trailer()

        assert trailer == ["0 TRLR"]

    def test_format_simple_person(self):
        """Test formatting a simple person"""
        formatter = GEDCOMFormatter()
        person = Person(
            id="I0001",
            given_names="Johannes",
            surname="van Berg",
            birth_date="1850-03-15",
            birth_place="Amsterdam"
        )

        lines = formatter._format_individual(person)

        assert lines[0] == "0 @I0001@ INDI"
        assert "1 NAME Johannes /van Berg/" in lines
        assert "2 GIVN Johannes" in lines
        assert "2 SURN van Berg" in lines
        assert "1 BIRT" in lines
        assert "2 DATE 1850-03-15" in lines
        assert "2 PLAC Amsterdam" in lines

    def test_format_person_with_tussenvoegsel(self):
        """Test formatting person with Dutch tussenvoegsel"""
        formatter = GEDCOMFormatter()
        person = Person(
            id="I0002",
            given_names="Maria",
            tussenvoegsel="van der",
            surname="Berg",
            death_date="1920-12-03"
        )

        lines = formatter._format_individual(person)

        assert "1 NAME Maria /van der Berg/" in lines
        assert "2 GIVN Maria" in lines
        assert "2 SURN Berg" in lines
        assert "2 NPFX van der" in lines
        assert "1 DEAT" in lines
        assert "2 DATE 1920-12-03" in lines

    def test_format_person_with_baptism(self):
        """Test formatting person with baptism information"""
        formatter = GEDCOMFormatter()
        person = Person(
            id="I0003",
            given_names="Pieter",
            surname="de Jong",
            baptism_date="1855-04-10",
            baptism_place="Gereformeerde Kerk Amsterdam"
        )

        lines = formatter._format_individual(person)

        assert "1 BAPM" in lines
        assert "2 DATE 1855-04-10" in lines
        assert "2 PLAC Gereformeerde Kerk Amsterdam" in lines

    def test_format_person_with_notes(self):
        """Test formatting person with notes"""
        formatter = GEDCOMFormatter()
        person = Person(
            id="I0004",
            given_names="Anna",
            surname="Smit",
            notes="Baker by profession. Lived in Amsterdam most of her life."
        )

        lines = formatter._format_individual(person)

        assert "1 NOTE Baker by profession. Lived in Amsterdam most of her life." in lines

    def test_format_person_with_long_notes(self):
        """Test formatting person with long notes that need splitting"""
        formatter = GEDCOMFormatter()
        long_note = "This is a very long note that exceeds the typical GEDCOM line length limit and should be split into multiple lines for proper formatting."
        person = Person(
            id="I0005",
            given_names="Willem",
            surname="Peters",
            notes=long_note
        )

        lines = formatter._format_individual(person)

        # Should have NOTE line and CONT lines
        note_lines = [line for line in lines if line.startswith(("1 NOTE", "2 CONT"))]
        assert len(note_lines) > 1
        assert note_lines[0].startswith("1 NOTE")
        assert all(line.startswith("2 CONT") for line in note_lines[1:])

    def test_format_person_with_occupations(self):
        """Test formatting person with occupations"""
        formatter = GEDCOMFormatter()
        person = Person(
            id="I0006",
            given_names="Jan",
            surname="Bakker",
            occupations=["Baker", "Miller"]
        )

        lines = formatter._format_individual(person)

        assert "1 OCCU Baker" in lines
        assert "1 OCCU Miller" in lines

    def test_format_gender_detection(self):
        """Test gender detection from Dutch names"""
        formatter = GEDCOMFormatter()

        with patch('web_app.shared.dutch_utils.DutchNameParser') as mock_parser:
            mock_parser.detect_gender.return_value = "M"

            person = Person(id="I0007", given_names="Johannes", surname="de Vries")
            lines = formatter._format_individual(person)

            assert "1 SEX M" in lines
            mock_parser.detect_gender.assert_called_once_with("Johannes")

    def test_format_family_with_parents_and_children(self):
        """Test formatting family with parents and children"""
        formatter = GEDCOMFormatter()

        family = Family(
            id="F0001",
            husband_id="I0001",
            wife_id="I0002",
            children_ids=["I0003", "I0004"]
        )

        lines = formatter._format_family(family)

        assert lines[0] == "0 @F0001@ FAM"
        assert "1 HUSB @II0001@" in lines
        assert "1 WIFE @II0002@" in lines
        assert "1 CHIL @II0003@" in lines
        assert "1 CHIL @II0004@" in lines

    def test_format_family_with_marriage_info(self):
        """Test formatting family with marriage information"""
        formatter = GEDCOMFormatter()

        family = Family(
            id="F0001",
            marriage_date="1875-06-15",
            marriage_place="Amsterdam"
        )

        lines = formatter._format_family(family)

        assert "1 MARR" in lines
        assert "2 DATE 1875-06-15" in lines
        assert "2 PLAC Amsterdam" in lines

    def test_format_complete_gedcom(self):
        """Test formatting complete GEDCOM with people and families"""
        formatter = GEDCOMFormatter()

        people = [
            Person(id="I0001", given_names="Jan", surname="de Vries"),
            Person(id="I0002", given_names="Maria", surname="Smit")
        ]
        families = [Family(id="F0001")]

        with patch('web_app.shared.gedcom_formatter.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "01 JAN 2024"

            lines = formatter.format_gedcom(people, families)

        # Should have header, individuals, families, and trailer
        assert lines[0] == "0 HEAD"
        assert lines[-1] == "0 TRLR"
        assert any("@I0001@ INDI" in line for line in lines)
        assert any("@I0002@ INDI" in line for line in lines)
        assert any("@F0001@ FAM" in line for line in lines)

    def test_split_note_short(self):
        """Test note splitting for short notes"""
        formatter = GEDCOMFormatter()
        note = "Short note"

        result = formatter._split_note(note)

        assert result == ["Short note"]

    def test_split_note_long(self):
        """Test note splitting for long notes"""
        formatter = GEDCOMFormatter()
        note = "This is a very long note that definitely exceeds the maximum line length and should be properly split into multiple lines"

        result = formatter._split_note(note, max_length=30)

        assert len(result) > 1
        assert all(len(line) <= 30 for line in result)
        assert " ".join(result) == note

    def test_person_counter_increments(self):
        """Test that person counter increments correctly"""
        formatter = GEDCOMFormatter()

        person1 = Person(id="I0001", given_names="Jan", surname="de Vries")
        person2 = Person(id="I0002", given_names="Maria", surname="Smit")

        lines1 = formatter._format_individual(person1)
        lines2 = formatter._format_individual(person2)

        assert "@I0001@" in lines1[0]
        assert "@I0002@" in lines2[0]

    def test_family_counter_increments(self):
        """Test that family counter increments correctly"""
        formatter = GEDCOMFormatter()

        family1 = Family(id="F0001")
        family2 = Family(id="F0002")

        lines1 = formatter._format_family(family1)
        lines2 = formatter._format_family(family2)

        assert "@F0001@" in lines1[0]
        assert "@F0002@" in lines2[0]


class TestGEDCOMFileWriter:
    """Test GEDCOM file I/O operations"""

    def test_write_gedcom_file(self):
        """Test writing GEDCOM lines to file"""
        lines = [
            "0 HEAD",
            "1 SOUR Test",
            "0 @I0001@ INDI",
            "1 NAME John /Doe/",
            "0 TRLR"
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged') as tmp_file:
            tmp_path = tmp_file.name

        try:
            GEDCOMFileWriter.write_gedcom_file(lines, tmp_path)

            # Verify file was written correctly
            with open(tmp_path, encoding='utf-8') as f:
                content = f.read()

            expected = "0 HEAD\n1 SOUR Test\n0 @I0001@ INDI\n1 NAME John /Doe/\n0 TRLR"
            assert content == expected

        finally:
            Path(tmp_path).unlink()

    def test_read_gedcom_file(self):
        """Test reading GEDCOM lines from file"""
        content = "0 HEAD\n1 SOUR Test\n0 @I0001@ INDI\n1 NAME John /Doe/\n0 TRLR"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ged') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            lines = GEDCOMFileWriter.read_gedcom_file(tmp_path)

            expected = [
                "0 HEAD",
                "1 SOUR Test",
                "0 @I0001@ INDI",
                "1 NAME John /Doe/",
                "0 TRLR"
            ]
            assert lines == expected

        finally:
            Path(tmp_path).unlink()
