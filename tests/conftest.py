"""
Pytest configuration and fixtures for family wiki project
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_gedcom_data():
    """Sample GEDCOM data for testing"""
    return """0 HEAD
1 SOUR Family Tree Maker
1 GEDC
2 VERS 5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Jan /van Bulhuis/
2 GIVN Jan
2 SURN van Bulhuis
1 SEX M
1 BIRT
2 DATE 1 JAN 1800
2 PLAC Amsterdam, Netherlands
1 DEAT
2 DATE 31 DEC 1870
2 PLAC Amsterdam, Netherlands
0 TRLR"""

@pytest.fixture
def sample_llm_result():
    """Sample LLM extraction result for testing"""
    return {
        "persons": [
            {
                "id": "person_1",
                "name": "Jan van Bulhuis",
                "birth_date": "1800-01-01",
                "birth_place": "Amsterdam",
                "death_date": "1870-12-31",
                "death_place": "Amsterdam",
                "confidence": 0.95
            }
        ],
        "families": [],
        "events": [
            {
                "type": "birth",
                "person_id": "person_1",
                "date": "1800-01-01",
                "place": "Amsterdam",
                "confidence": 0.90
            }
        ]
    }