"""
Tests for database integration and our specific business logic
"""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tests.conftest import BaseTestConfig
from web_app import Config, create_app
from web_app.database import db, init_db
from web_app.database.models import Person, Place, SourceText, TextCorpus


class DatabaseTestConfig(BaseTestConfig):
    """Test configuration for database tests"""
    def __init__(self):
        super().__init__()



class TestDatabaseInitialization:
    """Test our database initialization logic"""

    @patch('web_app.services.prompt_service.PromptService')
    def test_init_db_loads_default_prompts(self, mock_prompt_service_class, app):
        """Test that init_db calls our prompt loading logic"""
        with app.app_context():
            # Mock the prompt service instance and its load_default_prompts method
            mock_prompt_service_instance = mock_prompt_service_class.return_value
            mock_prompt = MagicMock()
            mock_prompt.name = "Test Prompt"
            mock_prompt_service_instance.load_default_prompts.return_value = [mock_prompt]

            # Initialize database
            init_db()

            # Verify our prompt service was instantiated and load_default_prompts was called
            mock_prompt_service_class.assert_called_once()
            mock_prompt_service_instance.load_default_prompts.assert_called_once()

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
            db.session.flush()

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
            db.session.flush()

            # Test parent-child relationships
            father.children.extend([child1, child2])
            mother.children.extend([child1, child2])
            db.session.flush()

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
            db.session.flush()

            # Verify our extraction tracking fields
            assert person.extraction_chunk_id == 42
            assert person.extraction_method == "llm"
            assert person.confidence_score == 0.85


    def test_place_deduplication_by_name(self, app):
        """Test that our Place model prevents duplicate place names"""
        with app.app_context():
            db.create_all()

            # Create first place
            place1 = Place(name="Amsterdam", country="Netherlands")
            db.session.add(place1)
            db.session.flush()

            # Try to create duplicate place name
            place2 = Place(name="Amsterdam", country="Germany")
            db.session.add(place2)

            # Should raise integrity error due to unique constraint
            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError):  # SQLAlchemy will raise an IntegrityError
                db.session.flush()

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
            db.session.flush()

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
            db.session.flush()

            # Test our chunk_count business logic
            assert corpus.chunk_count == 2

            # Test chunk organization by file and page
            page_1_chunks = SourceText.query.filter_by(
                corpus_id=corpus.id,
                filename="page_001.txt",
                page_number=1
            ).all()
            assert len(page_1_chunks) == 2

    def test_confidence_scoring_logic(self, app, db):
        """Test our confidence scoring business logic"""
        with app.app_context():
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
            db.session.flush()  # Make data available for queries within this transaction

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
            db.session.flush()

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
            db.session.flush()

            # Verify our RAG-specific fields are stored
            assert chunk.embedding_model == "test-model"
            assert chunk.token_count == 6
            assert chunk.content_hash is None  # Not set in this test



class TestCosineSimilarity:
    """Test cosine similarity calculation in SourceText model"""

    def test_identical_vectors(self):
        """Test that identical vectors have similarity of 1.0"""
        vec = [1, 2, 3, 4]
        similarity = SourceText.calculate_cosine_similarity(vec, vec)
        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        """Test that orthogonal vectors have similarity of 0.0"""
        vec1 = [1, 0, 0]
        vec2 = [0, 1, 0]
        similarity = SourceText.calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self):
        """Test that opposite vectors have similarity of -1.0"""
        vec1 = [1, 0, 0]
        vec2 = [-1, 0, 0]
        similarity = SourceText.calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(-1.0, abs=1e-6)

    def test_similar_vectors(self):
        """Test that similar vectors have high positive similarity"""
        vec1 = [1, 2, 3]
        vec2 = [1.1, 2.1, 3.1]  # Slightly scaled version
        similarity = SourceText.calculate_cosine_similarity(vec1, vec2)
        assert similarity > 0.99  # Should be very high

    def test_zero_vector_handling(self):
        """Test that zero vectors are handled gracefully"""
        vec1 = [0, 0, 0]
        vec2 = [1, 2, 3]

        # Zero vector with non-zero vector should return 0
        similarity1 = SourceText.calculate_cosine_similarity(vec1, vec2)
        assert similarity1 == 0.0

        # Both zero vectors should return 0
        similarity2 = SourceText.calculate_cosine_similarity(vec1, vec1)
        assert similarity2 == 0.0

    def test_numpy_array_input(self):
        """Test that numpy arrays work as input"""
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([4, 5, 6])
        similarity = SourceText.calculate_cosine_similarity(vec1, vec2)

        # Calculate expected similarity manually
        expected = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        assert similarity == pytest.approx(expected, abs=1e-6)

    def test_mixed_input_types(self):
        """Test that mixing lists and numpy arrays works"""
        vec1 = [1, 2, 3]
        vec2 = np.array([1, 2, 3])
        similarity = SourceText.calculate_cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_high_dimensional_vectors(self):
        """Test with high-dimensional vectors (typical embedding size)"""
        # Create random vectors of typical embedding dimension
        np.random.seed(42)  # For reproducible results
        vec1 = np.random.randn(384)  # Common embedding dimension
        vec2 = np.random.randn(384)

        similarity = SourceText.calculate_cosine_similarity(vec1, vec2)

        # Should be between -1 and 1
        assert -1 <= similarity <= 1

        # Calculate expected similarity manually
        expected = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        assert similarity == pytest.approx(expected, abs=1e-6)

    def test_real_world_embedding_example(self):
        """Test with realistic embedding vectors"""
        # Simulate embeddings for similar text chunks
        embedding1 = [0.1, 0.2, -0.3, 0.4, -0.1, 0.5, 0.2, -0.2]
        embedding2 = [0.15, 0.25, -0.25, 0.35, -0.05, 0.45, 0.25, -0.15]  # Similar
        embedding3 = [-0.1, -0.2, 0.3, -0.4, 0.1, -0.5, -0.2, 0.2]  # Opposite-ish

        # Similar embeddings should have high similarity
        similarity_similar = SourceText.calculate_cosine_similarity(embedding1, embedding2)
        assert similarity_similar > 0.8

        # Different embeddings should have lower similarity
        similarity_different = SourceText.calculate_cosine_similarity(embedding1, embedding3)
        assert similarity_different < similarity_similar
