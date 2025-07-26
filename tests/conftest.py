"""
Pytest configuration and fixtures for family wiki project
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from web_app import create_app
from web_app.database import db as _db


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


class BaseTestConfig:
    """Base test configuration that doesn't require environment variables"""
    def __init__(self):
        # App configuration
        self.secret_key = 'test-secret-key'

        # Database configuration
        self.sqlalchemy_database_uri = 'sqlite:///:memory:'
        self.sqlalchemy_track_modifications = False

        # Celery configuration
        self.celery_broker_url = 'redis://localhost:6379/0'
        self.celery_result_backend = 'redis://localhost:6379/1'

        # Ollama configuration
        self.ollama_host = 'localhost'
        self.ollama_port = 11434
        self.ollama_model = 'test-model'

    @property
    def ollama_base_url(self):
        return f"http://{self.ollama_host}:{self.ollama_port}"


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = create_app(BaseTestConfig())
    return app


@pytest.fixture
def db(app):
    """Create database for testing"""
    with app.app_context():
        # Import all models to ensure they're registered with SQLAlchemy
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def clean_db(db):
    """Fixture that provides a clean database by clearing all extraction data"""
    def _clean_db():
        """Clear all extraction data from the database"""
        from web_app.database.models import (
            Event,
            ExtractionPrompt,
            Family,
            JobFile,
            Marriage,
            OcrPage,
            Person,
            Place,
            Query,
            SourceText,
            TextCorpus,
        )

        # Delete in order to respect foreign key constraints
        Query.query.delete()
        SourceText.query.delete()
        TextCorpus.query.delete()
        Family.query.delete()
        Marriage.query.delete()
        Event.query.delete()
        Person.query.delete()
        Place.query.delete()
        OcrPage.query.delete()
        JobFile.query.delete()
        ExtractionPrompt.query.delete()

        db.session.commit()

    return _clean_db
