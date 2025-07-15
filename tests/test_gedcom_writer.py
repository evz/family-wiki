"""
Tests for GEDCOM writer (public interface)
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
        assert writer.formatter is not None
        assert writer.file_writer is not None
        assert writer.formatter.person_counter == 1
        assert writer.formatter.family_counter == 1
        assert writer.formatter.source_counter == 1

    def test_write_gedcom_empty_people(self):
        """Test writing GEDCOM with empty people list"""
        writer = GEDCOMWriter()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_file = f.name

        try:
            writer.write_gedcom([], output_file=temp_file)

            # Read the file and verify it has at least header and trailer
            with open(temp_file, encoding='utf-8') as f:
                content = f.read()

            assert "0 HEAD" in content
            assert "0 TRLR" in content

        finally:
            Path(temp_file).unlink()

    def test_write_gedcom_integration(self):
        """Test complete GEDCOM writing with people"""
        writer = GEDCOMWriter()

        people = [
            Person(
                id="person1",
                given_names="Jan",
                surname="Jansen",
                birth_date="1 JAN 1800"
            ),
            Person(
                id="person2",
                given_names="Maria",
                tussenvoegsel="van der",
                surname="Berg",
                baptism_date="8 JAN 1800",
                baptism_place="Amsterdam"
            )
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_file = f.name

        try:
            writer.write_gedcom(people, output_file=temp_file)

            # Read the file and verify content
            with open(temp_file, encoding='utf-8') as f:
                content = f.read()

            # Check header
            assert "0 HEAD" in content
            assert "1 SOUR VanBulhuisExtractor" in content
            assert "2 VERS 1.0" in content
            assert "1 GEDC" in content
            assert "2 VERS 5.5.1" in content
            assert "1 CHAR UTF-8" in content

            # Check individuals
            assert "0 @I0001@ INDI" in content
            assert "1 NAME Jan /Jansen/" in content
            assert "1 BIRT" in content
            assert "2 DATE 1 JAN 1800" in content

            assert "0 @I0002@ INDI" in content
            assert "1 NAME Maria /van der Berg/" in content
            assert "1 BAPM" in content
            assert "2 DATE 8 JAN 1800" in content
            assert "2 PLAC Amsterdam" in content

            # Check trailer
            assert "0 TRLR" in content

        finally:
            Path(temp_file).unlink()

    def test_write_gedcom_with_families(self):
        """Test writing GEDCOM with families"""
        writer = GEDCOMWriter()

        people = [
            Person(id="person1", given_names="Jan", surname="Jansen"),
            Person(id="person2", given_names="Maria", surname="Smit")
        ]

        families = [
            Family(id="family1", husband_id="I0001", wife_id="I0002")
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            temp_file = f.name

        try:
            writer.write_gedcom(people, families, output_file=temp_file)

            # Read the file and verify content
            with open(temp_file, encoding='utf-8') as f:
                content = f.read()

            # Check family record
            assert "0 @F0001@ FAM" in content
            assert "1 HUSB @II0001@" in content
            assert "1 WIFE @II0002@" in content

        finally:
            Path(temp_file).unlink()

    def test_backward_compatibility_methods(self):
        """Test backward compatibility methods"""
        writer = GEDCOMWriter()

        # Test add_person
        person = Person(id="person1", given_names="Jan", surname="Jansen")
        writer.add_person(person)

        assert hasattr(writer, 'people')
        assert len(writer.people) == 1
        assert writer.people[0] == person

        # Test add_family
        family = Family(id="family1", husband_id="I0001", wife_id="I0002")
        writer.add_family(family)

        assert hasattr(writer, 'families')
        assert len(writer.families) == 1
        assert writer.families[0] == family

        # Test generate method
        content = writer.generate()

        assert "0 HEAD" in content
        assert "0 @I0001@ INDI" in content
        assert "1 NAME Jan /Jansen/" in content
        assert "0 @F0001@ FAM" in content
        assert "0 TRLR" in content

    def test_write_gedcom_default_filename(self):
        """Test writing GEDCOM with default filename"""
        writer = GEDCOMWriter()

        people = [
            Person(id="person1", given_names="Test", surname="Person")
        ]

        try:
            writer.write_gedcom(people)  # Uses default filename

            # Check that the default file was created
            default_file = Path("family_tree.ged")
            assert default_file.exists()

            # Verify content
            with open(default_file, encoding='utf-8') as f:
                content = f.read()

            assert "0 HEAD" in content
            assert "0 @I0001@ INDI" in content
            assert "1 NAME Test /Person/" in content
            assert "0 TRLR" in content

        finally:
            # Clean up
            default_file = Path("family_tree.ged")
            if default_file.exists():
                default_file.unlink()
