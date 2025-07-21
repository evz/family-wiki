"""
Tests for database integration and our specific business logic
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest


# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import Config, create_app
from tests.conftest import BaseTestConfig
from web_app.database import db, init_db
from web_app.database.models import ExtractionPrompt, Person, Place, SourceText, TextCorpus
from web_app.services.prompt_service import prompt_service


class DatabaseTestConfig(BaseTestConfig):
    """Test configuration for database tests"""
    def __init__(self):
        super().__init__()


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app(DatabaseTestConfig())
    return app


class TestDatabaseInitialization:
    """Test our database initialization logic"""

    @patch('web_app.services.prompt_service.prompt_service.load_default_prompts')
    def test_init_db_loads_default_prompts(self, mock_load_prompts, app):
        """Test that init_db calls our prompt loading logic"""
        with app.app_context():
            # Mock the prompt service to return a fake prompt
            mock_prompt = MagicMock()
            mock_prompt.name = "Test Prompt"
            mock_load_prompts.return_value = [mock_prompt]

            # Initialize database
            init_db()

            # Verify our prompt loading was called
            mock_load_prompts.assert_called_once()

    def test_database_configuration_from_environment(self):
        """Test that database URL is configurable via environment"""
        env_vars = {
            'SECRET_KEY': 'test-secret',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'CELERY_BROKER_URL': 'redis://localhost:6379/0',
            'CELERY_RESULT_BACKEND': 'redis://localhost:6379/1',
            'OLLAMA_HOST': 'localhost',
            'OLLAMA_PORT': '11434',
            'OLLAMA_MODEL': 'test-model'
        }
        with patch.dict(os.environ, env_vars):
            config = Config()
            assert config.sqlalchemy_database_uri == 'postgresql://test:test@localhost/test'


class TestBusinessLogicConstraints:
    """Test our specific business logic and constraints"""

    def test_person_name_formatting_business_logic(self, app):
        """Test our Dutch name formatting business logic"""
        with app.app_context():
            db.create_all()

            # Test Dutch naming conventions
            person = Person(
                given_names="Johannes Wilhelmus",
                surname="Berg",
                tussenvoegsel="van der"
            )
            db.session.add(person)
            db.session.commit()

            # Test our specific Dutch name formatting
            assert person.full_name == "Johannes Wilhelmus van der Berg"
            assert person.display_name == "van der Berg, Johannes Wilhelmus"

            # Test without tussenvoegsel
            person_simple = Person(given_names="Maria", surname="Jansen")
            assert person_simple.full_name == "Maria Jansen"
            assert person_simple.display_name == "Jansen, Maria"

    def test_family_relationship_tracking(self, app):
        """Test our family relationship tracking logic"""
        with app.app_context():
            db.create_all()

            # Create family members
            father = Person(given_names="Johannes", surname="Berg")
            mother = Person(given_names="Maria", surname="Jansen")
            child1 = Person(given_names="Pieter", surname="Berg")
            child2 = Person(given_names="Anna", surname="Berg")

            db.session.add_all([father, mother, child1, child2])
            db.session.commit()

            # Test parent-child relationships
            father.children.extend([child1, child2])
            mother.children.extend([child1, child2])
            db.session.commit()

            # Verify bidirectional relationships work
            assert len(father.children) == 2
            assert len(mother.children) == 2
            assert father in child1.parents
            assert mother in child1.parents
            assert len(child1.parents) == 2

    def test_extraction_metadata_tracking(self, app):
        """Test our extraction metadata tracking"""
        with app.app_context():
            db.create_all()

            # Create person with extraction metadata
            person = Person(
                given_names="Johannes",
                surname="Berg",
                extraction_chunk_id=42,
                extraction_method="llm",
                confidence_score=0.85
            )
            db.session.add(person)
            db.session.commit()

            # Verify our extraction tracking fields
            assert person.extraction_chunk_id == 42
            assert person.extraction_method == "llm"
            assert person.confidence_score == 0.85

    def test_prompt_safety_constraints(self, app):
        """Test our prompt management safety constraints"""
        with app.app_context():
            db.create_all()

            # Create initial prompts
            prompt1 = ExtractionPrompt(
                name="Prompt 1",
                prompt_text="Text 1",
                is_active=True
            )
            prompt2 = ExtractionPrompt(
                name="Prompt 2",
                prompt_text="Text 2",
                is_active=False
            )
            db.session.add_all([prompt1, prompt2])
            db.session.commit()

            # Test safety constraint: can't delete active prompt
            result = prompt_service.delete_prompt(str(prompt1.id))
            assert result is False  # Should fail

            # Test safety constraint: can't delete if only one left
            prompt_service.delete_prompt(str(prompt2.id))  # Delete non-active
            result = prompt_service.delete_prompt(str(prompt1.id))  # Try to delete last one
            assert result is False  # Should fail

    def test_place_deduplication_by_name(self, app):
        """Test that our Place model prevents duplicate place names"""
        with app.app_context():
            db.create_all()

            # Create first place
            place1 = Place(name="Amsterdam", country="Netherlands")
            db.session.add(place1)
            db.session.commit()

            # Try to create duplicate place name
            place2 = Place(name="Amsterdam", country="Germany")
            db.session.add(place2)

            # Should raise integrity error due to unique constraint
            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError):  # SQLAlchemy will raise an IntegrityError
                db.session.commit()

    def test_text_corpus_chunk_relationship(self, app):
        """Test our text corpus and chunk relationship logic"""
        with app.app_context():
            db.create_all()

            # Create corpus
            corpus = TextCorpus(
                name="Dutch Family Book",
                description="Test corpus",
                chunk_size=1000,
                chunk_overlap=200
            )
            db.session.add(corpus)
            db.session.commit()

            # Add chunks
            chunk1 = SourceText(
                corpus=corpus,
                filename="page_001.txt",
                page_number=1,
                chunk_number=1,
                content="Johannes van der Berg was born in Amsterdam",
                token_count=8
            )
            chunk2 = SourceText(
                corpus=corpus,
                filename="page_001.txt",
                page_number=1,
                chunk_number=2,
                content="Maria Jansen married Johannes in 1825",
                token_count=7
            )
            db.session.add_all([chunk1, chunk2])
            db.session.commit()

            # Test our chunk_count business logic
            assert corpus.chunk_count == 2

            # Test chunk organization by file and page
            page_1_chunks = SourceText.query.filter_by(
                corpus_id=corpus.id,
                filename="page_001.txt",
                page_number=1
            ).all()
            assert len(page_1_chunks) == 2

    def test_confidence_scoring_logic(self, app):
        """Test our confidence scoring business logic"""
        with app.app_context():
            db.create_all()

            # Create people with different confidence scores
            high_confidence = Person(
                given_names="Johannes",
                surname="Berg",
                confidence_score=0.95,
                notes="Explicitly mentioned with full details"
            )
            medium_confidence = Person(
                given_names="Maria",
                surname="Unknown",
                confidence_score=0.70,
                notes="Inferred from context"
            )
            low_confidence = Person(
                given_names="Unknown",
                surname="Jansen",
                confidence_score=0.40,
                notes="Uncertain identification"
            )

            db.session.add_all([high_confidence, medium_confidence, low_confidence])
            db.session.commit()

            # Test querying by confidence threshold (our business logic)
            high_quality_people = Person.query.filter(Person.confidence_score >= 0.80).all()
            assert len(high_quality_people) == 1
            assert high_quality_people[0].given_names == "Johannes"

            uncertain_people = Person.query.filter(Person.confidence_score < 0.60).all()
            assert len(uncertain_people) == 1
            assert uncertain_people[0].surname == "Jansen"


class TestRAGFunctionality:
    """Test our RAG (Retrieval-Augmented Generation) specific functionality"""

    def test_source_text_embedding_structure(self, app):
        """Test that our SourceText model supports embedding vectors"""
        with app.app_context():
            db.create_all()

            corpus = TextCorpus(name="Test Corpus", description="Test")
            db.session.add(corpus)
            db.session.commit()

            # Create text chunk with mock embedding
            chunk = SourceText(
                corpus=corpus,
                filename="test.txt",
                content="Test content about Johannes van der Berg",
                embedding_model="test-model",
                token_count=6
                # Note: In real usage, embedding would be a vector, but we can't easily test pgvector in SQLite
            )
            db.session.add(chunk)
            db.session.commit()

            # Verify our RAG-specific fields are stored
            assert chunk.embedding_model == "test-model"
            assert chunk.token_count == 6
            assert chunk.content_hash is None  # Not set in this test

    def test_query_session_configuration(self, app):
        """Test our RAG query session configuration"""
        with app.app_context():
            db.create_all()

            corpus = TextCorpus(name="Test Corpus", description="Test")
            db.session.add(corpus)
            db.session.commit()

            # Test our query session business logic
            from web_app.database.models import QuerySession

            session = QuerySession(
                corpus=corpus,
                session_name="Test RAG Session",
                max_chunks=5,
                similarity_threshold=0.75
            )
            db.session.add(session)
            db.session.commit()

            # Verify our RAG configuration is stored correctly
            assert session.max_chunks == 5
            assert session.similarity_threshold == 0.75
            assert session.corpus.name == "Test Corpus"
