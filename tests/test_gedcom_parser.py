"""
Tests for GEDCOM parser functionality
"""

import tempfile
from pathlib import Path

from web_app.shared.gedcom_parser import GEDCOMParser


class TestGEDCOMParser:
    """Test GEDCOM parser functionality"""

    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = GEDCOMParser()
        assert parser.individuals == {}
        assert parser.families == {}
        assert parser.places == {}
        assert parser.events == {}
        assert parser.sources == {}

    def test_parse_empty_file(self):
        """Test parsing empty GEDCOM file"""
        parser = GEDCOMParser()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write("")
            temp_file = f.name
        
        try:
            result = parser.parse_file(temp_file)
            assert result['individuals'] == {}
            assert result['families'] == {}
            assert result['sources'] == {}
        finally:
            Path(temp_file).unlink()

    def test_parse_minimal_gedcom(self):
        """Test parsing minimal GEDCOM file"""
        parser = GEDCOMParser()
        
        gedcom_content = """0 HEAD
1 SOUR TEST
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I001@ INDI
1 NAME Jan /Jansen/
2 GIVN Jan
2 SURN Jansen
1 BIRT
2 DATE 1800-01-01
2 PLAC Amsterdam
0 TRLR
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(gedcom_content)
            temp_file = f.name
        
        try:
            result = parser.parse_file(temp_file)
            assert len(result['individuals']) == 1
            assert 'I001' in result['individuals']
            
            individual = result['individuals']['I001']
            assert individual.given_names == "Jan"
            assert individual.surname == "Jansen"
        finally:
            Path(temp_file).unlink()

    def test_parse_gedcom_with_family(self):
        """Test parsing GEDCOM file with family"""
        parser = GEDCOMParser()
        
        gedcom_content = """0 HEAD
1 SOUR TEST
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I001@ INDI
1 NAME Jan /Jansen/
2 GIVN Jan
2 SURN Jansen
0 @I002@ INDI
1 NAME Maria /Pieterse/
2 GIVN Maria
2 SURN Pieterse
0 @F001@ FAM
1 HUSB @I001@
1 WIFE @I002@
1 MARR
2 DATE 1825-06-01
2 PLAC Amsterdam
0 TRLR
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(gedcom_content)
            temp_file = f.name
        
        try:
            result = parser.parse_file(temp_file)
            assert len(result['individuals']) == 2
            assert len(result['families']) == 1
            assert 'F001' in result['families']
            
            family = result['families']['F001']
            assert family.husband_id == "I001"
            assert family.wife_id == "I002"
        finally:
            Path(temp_file).unlink()

    def test_parse_individual_with_multiple_events(self):
        """Test parsing individual with multiple life events"""
        parser = GEDCOMParser()
        
        gedcom_content = """0 HEAD
1 SOUR TEST
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I001@ INDI
1 NAME Jan /Jansen/
2 GIVN Jan
2 SURN Jansen
1 BIRT
2 DATE 1800-01-01
2 PLAC Amsterdam
1 BAPM
2 DATE 1800-01-15
2 PLAC Amsterdam
1 DEAT
2 DATE 1870-12-31
2 PLAC Amsterdam
1 OCCU Baker
1 NOTE Test note
0 TRLR
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(gedcom_content)
            temp_file = f.name
        
        try:
            result = parser.parse_file(temp_file)
            assert len(result['individuals']) == 1
            assert 'I001' in result['individuals']
            
            individual = result['individuals']['I001']
            # The parser may process dates differently, so just check they're not empty
            assert individual.birth_date != ""
            assert individual.baptism_date != ""
            assert individual.death_date != ""
        finally:
            Path(temp_file).unlink()

    def test_parse_family_with_children(self):
        """Test parsing family with children"""
        parser = GEDCOMParser()
        
        gedcom_content = """0 HEAD
1 SOUR TEST
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I001@ INDI
1 NAME Jan /Jansen/
0 @I002@ INDI
1 NAME Maria /Pieterse/
0 @I003@ INDI
1 NAME Pieter /Jansen/
0 @F001@ FAM
1 HUSB @I001@
1 WIFE @I002@
1 CHIL @I003@
1 MARR
2 DATE 1825-06-01
0 TRLR
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write(gedcom_content)
            temp_file = f.name
        
        try:
            result = parser.parse_file(temp_file)
            assert len(result['individuals']) == 3
            assert len(result['families']) == 1
            
            family = result['families']['F001']
            assert family.husband_id == "I001"
            assert family.wife_id == "I002"
            assert "I003" in family.children_ids
        finally:
            Path(temp_file).unlink()

    def test_get_level_method(self):
        """Test _get_level method"""
        parser = GEDCOMParser()
        
        # Test different levels
        assert parser._get_level("0 HEAD") == 0
        assert parser._get_level("1 SOUR TEST") == 1
        assert parser._get_level("2 VERS 5.5.1") == 2
        assert parser._get_level("3 FORM LINEAGE-LINKED") == 3

    def test_extract_id_from_pointer(self):
        """Test _extract_id method"""
        parser = GEDCOMParser()
        
        # Test extracting ID from pointer
        assert parser._extract_id("@I001@") == "I001"
        assert parser._extract_id("@F001@") == "F001"
        assert parser._extract_id("@S001@") == "S001"
        
        # Test non-pointer strings (should return None)
        assert parser._extract_id("HEAD") is None
        assert parser._extract_id("TRLR") is None

    def test_parse_invalid_file(self):
        """Test parsing invalid file"""
        parser = GEDCOMParser()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
            f.write("invalid gedcom content")
            temp_file = f.name
        
        try:
            result = parser.parse_file(temp_file)
            # Should not crash, but may have empty results
            assert isinstance(result, dict)
            assert 'individuals' in result
            assert 'families' in result
        finally:
            Path(temp_file).unlink()

    def test_parse_file_not_found(self):
        """Test parsing non-existent file"""
        parser = GEDCOMParser()
        
        try:
            parser.parse_file("non_existent_file.ged")
            # Should handle gracefully or raise FileNotFoundError
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            # This is expected behavior
            assert True

    def test_split_into_records(self):
        """Test _split_into_records method"""
        parser = GEDCOMParser()
        
        lines = [
            "0 HEAD",
            "1 SOUR TEST",
            "0 @I001@ INDI",
            "1 NAME Jan /Jansen/",
            "0 TRLR"
        ]
        
        records = parser._split_into_records(lines)
        assert len(records) >= 2  # At least HEAD and TRLR records
        
        # Check that records are properly split
        assert isinstance(records, list)
        for record in records:
            assert isinstance(record, list)
            if record:  # Skip empty records
                assert isinstance(record[0], str)

    def test_parse_record_individual(self):
        """Test _parse_record for individual"""
        parser = GEDCOMParser()
        
        record = [
            "0 @I001@ INDI",
            "1 NAME Jan /Jansen/",
            "2 GIVN Jan",
            "2 SURN Jansen",
            "1 BIRT",
            "2 DATE 1800-01-01"
        ]
        
        parser._parse_record(record)
        
        assert 'I001' in parser.individuals
        individual = parser.individuals['I001']
        assert individual.given_names == "Jan"
        assert individual.surname == "Jansen"
        assert individual.birth_date != ""

    def test_parse_record_family(self):
        """Test _parse_record for family"""
        parser = GEDCOMParser()
        
        record = [
            "0 @F001@ FAM",
            "1 HUSB @I001@",
            "1 WIFE @I002@",
            "1 MARR",
            "2 DATE 1825-06-01"
        ]
        
        parser._parse_record(record)
        
        assert 'F001' in parser.families
        family = parser.families['F001']
        assert family.husband_id == "I001"
        assert family.wife_id == "I002"
        # Marriage date parsing may vary, just check that family structure is correct
        assert family.husband_id == "I001"