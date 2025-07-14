"""
Tests for GEDCOM writer
"""

import tempfile
from pathlib import Path

from web_app.shared.gedcom_writer import GEDCOMWriter
from web_app.shared.models import Family, Person


class TestGEDCOMWriter:
    """Test GEDCOM writer functionality"""

    def test_writer_initialization(self):
        """Test writer initialization"""
        writer = GEDCOMWriter()
        assert writer.lines == []
        assert writer.person_counter == 1
        assert writer.family_counter == 1
        assert writer.source_counter == 1

    def test_write_gedcom_empty_people(self):
        """Test writing GEDCOM with empty people list"""
        writer = GEDCOMWriter()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_file = f.name

        try:
            writer.write_gedcom([], output_file=temp_file)

            # Check file was created
            assert Path(temp_file).exists()

            # Check basic structure
            with open(temp_file) as f:
                content = f.read()
                assert "0 HEAD" in content
                assert "0 TRLR" in content
        finally:
            Path(temp_file).unlink()

    def test_write_gedcom_single_person(self):
        """Test writing GEDCOM with single person"""
        writer = GEDCOMWriter()

        # Create a test person
        person = Person(
            id="person1",
            given_names="Jan",
            surname="Jansen",
            birth_date="1800-01-01",
            birth_place="Amsterdam",
            death_date="1870-12-31",
            death_place="Amsterdam"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_file = f.name

        try:
            writer.write_gedcom([person], output_file=temp_file)

            # Check file was created
            assert Path(temp_file).exists()

            # Check content
            with open(temp_file) as f:
                content = f.read()
                assert "0 HEAD" in content
                assert "0 @I0001@ INDI" in content
                assert "1 NAME Jan /Jansen/" in content
                assert "1 BIRT" in content
                assert "2 DATE 1800-01-01" in content
                assert "2 PLAC Amsterdam" in content
                assert "1 DEAT" in content
                assert "2 DATE 1870-12-31" in content
                assert "0 TRLR" in content
        finally:
            Path(temp_file).unlink()

    def test_write_gedcom_with_families(self):
        """Test writing GEDCOM with families"""
        writer = GEDCOMWriter()

        # Create test persons
        father = Person(
            id="father1",
            given_names="Jan",
            surname="Jansen",
            birth_date="1800-01-01"
        )
        mother = Person(
            id="mother1",
            given_names="Maria",
            surname="Jansen",
            birth_date="1805-01-01"
        )
        child = Person(
            id="child1",
            given_names="Pieter",
            surname="Jansen",
            birth_date="1825-01-01"
        )

        # Create test family
        family = Family(
            id="family1",
            husband_id="father1",
            wife_id="mother1",
            children_ids=["child1"]
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_file = f.name

        try:
            writer.write_gedcom([father, mother, child], families=[family], output_file=temp_file)

            # Check file was created
            assert Path(temp_file).exists()

            # Check content
            with open(temp_file) as f:
                content = f.read()
                assert "0 HEAD" in content
                assert "0 @I0001@ INDI" in content
                assert "0 @I0002@ INDI" in content
                assert "0 @I0003@ INDI" in content
                assert "0 @F0001@ FAM" in content
                assert "0 TRLR" in content
        finally:
            Path(temp_file).unlink()

    def test_write_header(self):
        """Test writing GEDCOM header"""
        writer = GEDCOMWriter()
        writer._write_header()

        assert "0 HEAD" in writer.lines
        assert "1 SOUR VanBulhuisExtractor" in writer.lines
        assert "2 VERS 1.0" in writer.lines
        assert "1 GEDC" in writer.lines
        assert "2 VERS 5.5.1" in writer.lines
        assert "1 CHAR UTF-8" in writer.lines

    def test_write_trailer(self):
        """Test writing GEDCOM trailer"""
        writer = GEDCOMWriter()
        writer._write_trailer()

        assert "0 TRLR" in writer.lines

    def test_write_individual_minimal(self):
        """Test writing individual with minimal data"""
        writer = GEDCOMWriter()

        person = Person(
            id="person1",
            given_names="Jan",
            surname="Jansen"
        )

        writer._write_individual(person)

        lines = writer.lines
        assert "0 @I0001@ INDI" in lines
        assert "1 NAME Jan /Jansen/" in lines

    def test_write_individual_with_tussenvoegsel(self):
        """Test writing individual with Dutch tussenvoegsel"""
        writer = GEDCOMWriter()

        person = Person(
            id="person1",
            given_names="Jan",
            tussenvoegsel="van der",
            surname="Berg"
        )

        writer._write_individual(person)

        lines = writer.lines
        assert "0 @I0001@ INDI" in lines
        assert "1 NAME Jan /van der Berg/" in lines

    def test_write_individual_with_dates(self):
        """Test writing individual with birth and death dates"""
        writer = GEDCOMWriter()

        person = Person(
            id="person1",
            given_names="Jan",
            surname="Jansen",
            birth_date="1800-01-01",
            death_date="1870-12-31"
        )

        writer._write_individual(person)

        lines = writer.lines
        assert "1 BIRT" in lines
        assert "2 DATE 1800-01-01" in lines
        assert "1 DEAT" in lines
        assert "2 DATE 1870-12-31" in lines

    def test_write_individual_with_baptism(self):
        """Test writing individual with baptism date"""
        writer = GEDCOMWriter()

        person = Person(
            id="person1",
            given_names="Jan",
            surname="Jansen",
            baptism_date="1800-01-15"
        )

        writer._write_individual(person)

        lines = writer.lines
        assert "1 BAPM" in lines
        assert "2 DATE 1800-01-15" in lines

    def test_write_individual_with_notes(self):
        """Test writing individual with notes"""
        writer = GEDCOMWriter()

        person = Person(
            id="person1",
            given_names="Jan",
            surname="Jansen",
            notes="Test note"
        )

        writer._write_individual(person)

        lines = writer.lines
        assert "1 NOTE Test note" in lines

    def test_write_family_minimal(self):
        """Test writing family with minimal data"""
        writer = GEDCOMWriter()

        family = Family(
            id="family1",
            husband_id="father1",
            wife_id="mother1"
        )

        # Set up person IDs (simulate they were already written)
        writer.person_counter = 3

        writer._write_family(family)

        lines = writer.lines
        assert "0 @F0001@ FAM" in lines


    def test_person_counter_increment(self):
        """Test person counter increments correctly"""
        writer = GEDCOMWriter()

        person1 = Person(id="person1", given_names="Jan", surname="Jansen")
        person2 = Person(id="person2", given_names="Maria", surname="Jansen")

        writer._write_individual(person1)
        writer._write_individual(person2)

        assert "0 @I0001@ INDI" in writer.lines
        assert "0 @I0002@ INDI" in writer.lines
        assert writer.person_counter == 3

    def test_family_counter_increment(self):
        """Test family counter increments correctly"""
        writer = GEDCOMWriter()

        family1 = Family(id="family1", husband_id="father1", wife_id="mother1")
        family2 = Family(id="family2", husband_id="father2", wife_id="mother2")

        writer._write_family(family1)
        writer._write_family(family2)

        assert "0 @F0001@ FAM" in writer.lines
        assert "0 @F0002@ FAM" in writer.lines
        assert writer.family_counter == 3
