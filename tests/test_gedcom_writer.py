"""
Tests for GEDCOM writer functionality
"""
from unittest.mock import Mock, patch

import pytest

from web_app.database.models import Family, Person
from web_app.shared.gedcom_writer import GEDCOMWriter


class TestGEDCOMWriter:
    """Test GEDCOM writer functionality"""

    @pytest.fixture
    def writer(self):
        """Create GEDCOMWriter instance"""
        return GEDCOMWriter()

    @pytest.fixture
    def sample_person(self, app):
        """Create sample Person for testing"""
        person = Mock()
        person.id = "P1"
        person.given_names = "John"
        person.surname = "Doe"
        person.birth_date = "1980-01-01"
        return person

    @pytest.fixture
    def sample_family(self, app):
        """Create sample Family for testing"""
        family = Mock()
        family.id = "F1"
        family.husband_id = "P1"
        family.wife_id = "P2"
        return family

    def test_initialization(self, writer):
        """Test GEDCOMWriter initialization"""
        assert writer.formatter is not None
        assert writer.file_writer is not None

    @patch('web_app.shared.gedcom_writer.GEDCOMFormatter')
    @patch('web_app.shared.gedcom_writer.GEDCOMFileWriter')
    def test_initialization_with_mocks(self, mock_file_writer_class, mock_formatter_class):
        """Test initialization creates correct instances"""
        mock_formatter = Mock()
        mock_file_writer = Mock()
        mock_formatter_class.return_value = mock_formatter
        mock_file_writer_class.return_value = mock_file_writer
        
        writer = GEDCOMWriter()
        
        assert writer.formatter == mock_formatter
        assert writer.file_writer == mock_file_writer
        mock_formatter_class.assert_called_once()
        mock_file_writer_class.assert_called_once()

    def test_write_gedcom_with_people_only(self, writer, sample_person):
        """Test writing GEDCOM with people only"""
        people = [sample_person]
        
        with patch.object(writer.formatter, 'format_gedcom') as mock_format, \
             patch.object(writer.file_writer, 'write_gedcom_file') as mock_write:
            
            mock_format.return_value = ["0 HEAD", "1 GEDC", "0 TRLR"]
            
            writer.write_gedcom(people, output_file="test.ged")
            
            mock_format.assert_called_once_with(people, None)
            mock_write.assert_called_once_with(["0 HEAD", "1 GEDC", "0 TRLR"], "test.ged")

    def test_write_gedcom_with_people_and_families(self, writer, sample_person, sample_family):
        """Test writing GEDCOM with people and families"""
        people = [sample_person]
        families = [sample_family]
        
        with patch.object(writer.formatter, 'format_gedcom') as mock_format, \
             patch.object(writer.file_writer, 'write_gedcom_file') as mock_write:
            
            mock_format.return_value = ["0 HEAD", "1 GEDC", "0 @P1@ INDI", "0 @F1@ FAM", "0 TRLR"]
            
            writer.write_gedcom(people, families, "family.ged")
            
            mock_format.assert_called_once_with(people, families)
            mock_write.assert_called_once_with(
                ["0 HEAD", "1 GEDC", "0 @P1@ INDI", "0 @F1@ FAM", "0 TRLR"], 
                "family.ged"
            )

    def test_write_gedcom_default_filename(self, writer, sample_person):
        """Test writing GEDCOM with default filename"""
        people = [sample_person]
        
        with patch.object(writer.formatter, 'format_gedcom') as mock_format, \
             patch.object(writer.file_writer, 'write_gedcom_file') as mock_write:
            
            mock_format.return_value = ["0 HEAD", "0 TRLR"]
            
            writer.write_gedcom(people)
            
            mock_write.assert_called_once_with(["0 HEAD", "0 TRLR"], "family_tree.ged")

    def test_generate_backward_compatibility(self, writer, app):
        """Test generate method for backward compatibility"""
        # Set up the writer with some data for backward compatibility mode
        writer.people = [Mock()]
        writer.families = [Mock()]
        
        with patch.object(writer.formatter, 'format_gedcom') as mock_format:
            mock_format.return_value = ["0 HEAD", "1 GEDC", "0 TRLR"]
            
            result = writer.generate()
            
            assert result == "0 HEAD\n1 GEDC\n0 TRLR"
            mock_format.assert_called_once_with(writer.people, writer.families)

    def test_generate_without_data(self, writer, app):
        """Test generate method without any data"""
        with patch.object(writer.formatter, 'format_gedcom') as mock_format:
            mock_format.return_value = ["0 HEAD", "0 TRLR"]
            
            # This should work even if people/families attributes don't exist
            result = writer.generate()
            
            assert result == "0 HEAD\n0 TRLR"
            # Should be called with None, None when attributes don't exist
            mock_format.assert_called_once_with(None, None)

    def test_add_person_first_person(self, writer, sample_person):
        """Test adding first person creates people list"""
        assert not hasattr(writer, 'people')
        
        writer.add_person(sample_person)
        
        assert hasattr(writer, 'people')
        assert len(writer.people) == 1
        assert writer.people[0] == sample_person

    def test_add_person_additional_person(self, writer, sample_person):
        """Test adding additional person to existing list"""
        # Add first person
        writer.add_person(sample_person)
        
        # Add second person
        second_person = Mock()
        second_person.id = "P2"
        writer.add_person(second_person)
        
        assert len(writer.people) == 2
        assert writer.people[0] == sample_person
        assert writer.people[1] == second_person

    def test_add_family_first_family(self, writer, sample_family):
        """Test adding first family creates families list"""
        assert not hasattr(writer, 'families')
        
        writer.add_family(sample_family)
        
        assert hasattr(writer, 'families')
        assert len(writer.families) == 1
        assert writer.families[0] == sample_family

    def test_add_family_additional_family(self, writer, sample_family):
        """Test adding additional family to existing list"""
        # Add first family
        writer.add_family(sample_family)
        
        # Add second family
        second_family = Mock()
        second_family.id = "F2"
        writer.add_family(second_family)
        
        assert len(writer.families) == 2
        assert writer.families[0] == sample_family
        assert writer.families[1] == second_family

    def test_backward_compatibility_workflow(self, writer, sample_person, sample_family):
        """Test complete backward compatibility workflow"""
        # Use the backward compatibility methods
        writer.add_person(sample_person)
        writer.add_family(sample_family)
        
        with patch.object(writer.formatter, 'format_gedcom') as mock_format:
            mock_format.return_value = ["0 HEAD", "0 @P1@ INDI", "0 @F1@ FAM", "0 TRLR"]
            
            result = writer.generate()
            
            assert result == "0 HEAD\n0 @P1@ INDI\n0 @F1@ FAM\n0 TRLR"
            mock_format.assert_called_once_with([sample_person], [sample_family])

    def test_mixed_usage_pattern(self, writer, sample_person, sample_family):
        """Test mixing new API with backward compatibility methods"""
        # Use backward compatibility methods first
        writer.add_person(sample_person)
        writer.add_family(sample_family)
        
        # Then use new API
        additional_person = Mock()
        additional_person.id = "P2"
        
        with patch.object(writer.formatter, 'format_gedcom') as mock_format, \
             patch.object(writer.file_writer, 'write_gedcom_file') as mock_write:
            
            mock_format.return_value = ["0 HEAD", "0 @P2@ INDI", "0 TRLR"]
            
            # New API should work independently of backward compatibility data
            writer.write_gedcom([additional_person], output_file="new.ged")
            
            mock_format.assert_called_once_with([additional_person], None)
            mock_write.assert_called_once_with(["0 HEAD", "0 @P2@ INDI", "0 TRLR"], "new.ged")

    def test_empty_lists(self, writer):
        """Test handling of empty lists"""
        with patch.object(writer.formatter, 'format_gedcom') as mock_format, \
             patch.object(writer.file_writer, 'write_gedcom_file') as mock_write:
            
            mock_format.return_value = ["0 HEAD", "0 TRLR"]
            
            writer.write_gedcom([], [])
            
            mock_format.assert_called_once_with([], [])
            mock_write.assert_called_once_with(["0 HEAD", "0 TRLR"], "family_tree.ged")

    def test_none_families_parameter(self, writer, sample_person):
        """Test explicit None for families parameter"""
        with patch.object(writer.formatter, 'format_gedcom') as mock_format, \
             patch.object(writer.file_writer, 'write_gedcom_file') as mock_write:
            
            mock_format.return_value = ["0 HEAD", "0 @P1@ INDI", "0 TRLR"]
            
            writer.write_gedcom([sample_person], None)
            
            mock_format.assert_called_once_with([sample_person], None)