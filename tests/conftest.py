"""
Pytest configuration and fixtures for family wiki project
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import psycopg2
import pytest
from sqlalchemy import event

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
    """Test configuration that requires PostgreSQL database"""
    def __init__(self):
        # App configuration
        self.secret_key = 'test-secret-key'

        # Database configuration - PostgreSQL required
        test_db_url = os.getenv('TEST_DATABASE_URL')
        if test_db_url:
            self.sqlalchemy_database_uri = test_db_url
        else:
            # Use dockerized PostgreSQL test database
            self.sqlalchemy_database_uri = 'postgresql://family_wiki_user:family_wiki_password@localhost:5432/family_wiki_test'

        # Database URI configured - let Flask-SQLAlchemy handle connections
        print(f"Using PostgreSQL test database: {self.sqlalchemy_database_uri}")

        self.sqlalchemy_track_modifications = False


        # Ollama configuration
        self.ollama_host = 'localhost'
        self.ollama_port = 11434
        self.ollama_model = 'test-model'

    @property
    def ollama_base_url(self):
        return f"http://{self.ollama_host}:{self.ollama_port}"


@pytest.fixture(scope="session")
def app():
    """Create Flask app for testing - session scoped to share with tables fixture"""
    app = create_app(BaseTestConfig())
    return app

@pytest.fixture
def test_config():
    """Get test configuration for checking database type"""
    return BaseTestConfig()

# All tests now require PostgreSQL - no conditional skipping needed

@pytest.fixture(scope="session", autouse=True)
def tables(app):
    """Create database tables once per test session"""
    with app.app_context():
        _db.create_all()
        yield
        _db.drop_all()
        # Dispose of all connections in the pool
        _db.engine.dispose()

@pytest.fixture
def db(app, tables):
    """Create database for testing with SAVEPOINT pattern for proper transaction handling"""
    
    with app.app_context():
        
        # One connection + outer transaction per test
        conn = _db.engine.connect()
        outer = conn.begin()  # BEGIN
        
        # (Re)bind Flask-SQLAlchemy's scoped session to this connection
        _db.session.remove()
        _db.session.configure(bind=conn, autoflush=False, expire_on_commit=False)
        
        # Start SAVEPOINT at the connection level
        nested = conn.begin_nested()  # SAVEPOINT
        
        # After each commit, re-open SAVEPOINT
        real_session = _db.session()  # unwrap scoped_session to a real Session
        
        @event.listens_for(real_session, "after_transaction_end")
        def restart_savepoint(sess, trans):
            # When the nested transaction ends, make a new SAVEPOINT
            if not conn.closed and conn.in_transaction() and not conn.in_nested_transaction():
                conn.begin_nested()

        try:
            yield _db
        finally:
            # Clean up: remove scoped session, rollback outer, close
            try:
                _db.session.remove()
            except Exception:
                pass
            try:
                # Rollback the outer transaction (which includes all savepoints)
                outer.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def db_no_transaction(app):
    """
    Database fixture for integration tests that avoids transaction conflicts.
    
    Use this instead of 'db' fixture when testing blueprints that manage their own
    transactions with 'with db.session.begin():'. The regular 'db' fixture creates
    a transaction that conflicts with blueprint transaction management.
    """
    with app.app_context():
        # Create tables without starting a transaction
        _db.create_all()
        
        try:
            yield _db
        finally:
            # Clean up: drop tables and close connections
            _db.drop_all()
            _db.session.close()
            _db.engine.dispose()


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

        db.session.flush()  # Use flush instead of commit for tests

    return _clean_db


