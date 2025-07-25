"""
SQLAlchemy models for Family Wiki entities with proper relationships and RAG support
"""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID as POSTGRESQL_UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.types import CHAR, TypeDecorator

from . import db


class UUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36)
    to store the UUID string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(POSTGRESQL_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class TextCorpus(db.Model):
    """Model for grouping related source documents for RAG queries"""
    __tablename__ = 'text_corpora'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    embedding_model = db.Column(db.String(100), default='sentence-transformers/all-MiniLM-L6-v2')
    chunk_size = db.Column(db.Integer, default=1000)
    chunk_overlap = db.Column(db.Integer, default=200)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    text_chunks = db.relationship('SourceText', back_populates='corpus', cascade='all, delete-orphan')

    @hybrid_property
    def chunk_count(self):
        return len(self.text_chunks)

    def __repr__(self):
        return f'<TextCorpus {self.name}>'


class SourceText(db.Model):
    """Model for storing source text chunks with embeddings for RAG"""
    __tablename__ = 'source_texts'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    corpus_id = db.Column(UUID(), db.ForeignKey('text_corpora.id'), nullable=False)

    # Source document info
    filename = db.Column(db.String(255), nullable=False)
    page_number = db.Column(db.Integer)
    chunk_number = db.Column(db.Integer)

    # Text content
    content = db.Column(db.Text, nullable=False)
    content_hash = db.Column(db.String(64))  # For deduplication

    # RAG/Embedding fields
    embedding = db.Column(Vector(1024))  # pgvector field for embeddings (adjust dimension as needed)
    embedding_model = db.Column(db.String(100))
    token_count = db.Column(db.Integer)

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    corpus = db.relationship('TextCorpus', back_populates='text_chunks')

    # Indexes for search
    __table_args__ = (
        db.Index('idx_source_text_content', 'content'),
        db.Index('idx_source_text_corpus', 'corpus_id'),
        db.Index('idx_source_text_file_page', 'filename', 'page_number'),
        # pgvector index for similarity search
        db.Index('idx_source_text_embedding', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )

    @classmethod
    def find_similar(cls, query_embedding, corpus_id=None, limit=5, similarity_threshold=0.7):
        """Find text chunks similar to the query embedding using cosine similarity"""
        query = cls.query.filter(cls.embedding.isnot(None))

        if corpus_id:
            query = query.filter(cls.corpus_id == corpus_id)

        # Use pgvector cosine distance (1 - cosine_similarity)
        # Lower distance = higher similarity
        query = query.order_by(cls.embedding.cosine_distance(query_embedding))

        if limit:
            query = query.limit(limit)

        results = query.all()

        # Filter by similarity threshold if specified
        if similarity_threshold:
            filtered_results = []
            for chunk in results:
                # Calculate similarity from distance
                distance = db.session.query(
                    chunk.embedding.cosine_distance(query_embedding)
                ).scalar()
                similarity = 1 - distance
                if similarity >= similarity_threshold:
                    filtered_results.append((chunk, similarity))
            return filtered_results

        return [(chunk, None) for chunk in results]

    def __repr__(self):
        return f'<SourceText {self.filename}:{self.page_number}:{self.chunk_number}>'


class QuerySession(db.Model):
    """Model for tracking user question-answering sessions"""
    __tablename__ = 'query_sessions'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    corpus_id = db.Column(UUID(), db.ForeignKey('text_corpora.id'), nullable=False)
    session_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # RAG configuration for this session
    max_chunks = db.Column(db.Integer, default=5)  # How many chunks to retrieve
    similarity_threshold = db.Column(db.Float, default=0.7)  # Minimum similarity score

    # Relationships
    corpus = db.relationship('TextCorpus')
    queries = db.relationship('Query', back_populates='session', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<QuerySession {self.session_name or self.id}>'


class Query(db.Model):
    """Model for individual questions and RAG responses"""
    __tablename__ = 'queries'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(UUID(), db.ForeignKey('query_sessions.id'), nullable=False)

    # Question and response
    question = db.Column(db.Text, nullable=False)
    question_embedding = db.Column(Vector(1024))  # pgvector field for question embedding
    answer = db.Column(db.Text)

    # RAG metadata
    retrieved_chunks = db.Column(db.JSON)  # List of chunk IDs that were used
    similarity_scores = db.Column(db.JSON)  # Similarity scores for retrieved chunks
    ollama_model = db.Column(db.String(100))
    processing_time_ms = db.Column(db.Integer)

    # Status
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    completed_at = db.Column(db.DateTime)

    # Relationships
    session = db.relationship('QuerySession', back_populates='queries')

    def __repr__(self):
        return f'<Query {self.question[:50]}...>'


class ExtractionPrompt(db.Model):
    """Model for storing and managing LLM extraction prompts"""
    __tablename__ = 'extraction_prompts'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    description = db.Column(db.Text)

    def __repr__(self):
        return f'<ExtractionPrompt {self.name}>'


class OcrPage(db.Model):
    """Model for storing OCR results per single-page PDF (e.g., 001.pdf, 002.pdf)"""
    __tablename__ = 'ocr_pages'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)

    # Batch grouping - multiple single-page PDFs uploaded together
    batch_id = db.Column(UUID(), nullable=False)

    # File identification
    filename = db.Column(db.String(255), nullable=False)  # e.g., "001.pdf"
    page_number = db.Column(db.Integer, nullable=False)   # extracted from filename: 001.pdf → 1
    file_path = db.Column(db.String(500))  # Original PDF file path

    # OCR results
    extracted_text = db.Column(db.Text)
    confidence_score = db.Column(db.Float)  # Overall confidence from OCR

    # Processing metadata
    ocr_engine = db.Column(db.String(50), default='tesseract')
    language = db.Column(db.String(10), default='nld')  # Dutch
    processing_time_ms = db.Column(db.Integer)

    # Status and error handling
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Ensure unique pages per batch
    __table_args__ = (
        db.UniqueConstraint('batch_id', 'filename', name='unique_batch_file'),
        db.Index('idx_ocr_batch', 'batch_id'),
        db.Index('idx_ocr_filename', 'filename'),
        db.Index('idx_ocr_status', 'status'),
    )

    def __repr__(self):
        return f'<OcrPage {self.filename}:page_{self.page_number}>'


# Association table for parent-child relationships
parent_child = db.Table('parent_child',
    db.Column('parent_id', UUID(), db.ForeignKey('persons.id'), primary_key=True),
    db.Column('child_id', UUID(), db.ForeignKey('persons.id'), primary_key=True)
)

# Association table for event participants
event_participants = db.Table('event_participants',
    db.Column('event_id', UUID(), db.ForeignKey('events.id'), primary_key=True),
    db.Column('person_id', UUID(), db.ForeignKey('persons.id'), primary_key=True),
    db.Column('role', db.String(100))  # bride, groom, witness, etc.
)

# Association table for person-place connections
person_places = db.Table('person_places',
    db.Column('person_id', UUID(), db.ForeignKey('persons.id'), primary_key=True),
    db.Column('place_id', UUID(), db.ForeignKey('places.id'), primary_key=True),
    db.Column('connection_type', db.String(100)),  # birth, death, residence, etc.
    db.Column('date', db.String(100)),
    db.Column('notes', db.Text)
)


class Person(db.Model):
    """Model for individuals in the family tree"""
    __tablename__ = 'persons'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)

    # External identifiers
    gedcom_id = db.Column(db.String(50))  # GEDCOM ID like "I1", "I2"

    # Name fields
    given_names = db.Column(db.String(255))
    surname = db.Column(db.String(255))
    tussenvoegsel = db.Column(db.String(50))  # Dutch particles (van, de, etc.)
    sex = db.Column(db.String(1))  # M, F, or null

    # Life events
    birth_date = db.Column(db.String(100))  # Flexible date format
    birth_place_id = db.Column(UUID(), db.ForeignKey('places.id'))
    baptism_date = db.Column(db.String(100))
    baptism_place_id = db.Column(UUID(), db.ForeignKey('places.id'))
    death_date = db.Column(db.String(100))
    death_place_id = db.Column(UUID(), db.ForeignKey('places.id'))

    # Additional information
    notes = db.Column(db.Text)
    confidence_score = db.Column(db.Float, default=0.0)

    # Extraction metadata
    extraction_chunk_id = db.Column(db.Integer)
    extraction_method = db.Column(db.String(50), default='llm')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    birth_place = db.relationship('Place', foreign_keys=[birth_place_id])
    baptism_place = db.relationship('Place', foreign_keys=[baptism_place_id])
    death_place = db.relationship('Place', foreign_keys=[death_place_id])

    # Parent-child relationships
    children = db.relationship('Person',
                              secondary=parent_child,
                              primaryjoin=id == parent_child.c.parent_id,
                              secondaryjoin=id == parent_child.c.child_id,
                              back_populates='parents')
    parents = db.relationship('Person',
                             secondary=parent_child,
                             primaryjoin=id == parent_child.c.child_id,
                             secondaryjoin=id == parent_child.c.parent_id,
                             back_populates='children')

    # Marriage relationships
    marriages_as_person1 = db.relationship('Marriage', foreign_keys='Marriage.person1_id', back_populates='person1')
    marriages_as_person2 = db.relationship('Marriage', foreign_keys='Marriage.person2_id', back_populates='person2')

    # Event participation
    events = db.relationship('Event', secondary=event_participants, back_populates='participants')

    # Place connections
    places = db.relationship('Place', secondary=person_places, back_populates='persons')

    # Occupations (one-to-many)
    occupations = db.relationship('Occupation', back_populates='person')

    # Family memberships
    families_as_father = db.relationship('Family', foreign_keys='Family.father_id', back_populates='father')
    families_as_mother = db.relationship('Family', foreign_keys='Family.mother_id', back_populates='mother')
    families_as_child = db.relationship('Family', secondary='family_children', back_populates='children')

    @property
    def full_name(self):
        """Get full name with proper Dutch formatting"""
        parts = [self.given_names or '']
        if self.tussenvoegsel:
            parts.append(self.tussenvoegsel)
        if self.surname:
            parts.append(self.surname)
        return " ".join(filter(None, parts))

    @property
    def display_name(self):
        """Get display name (surname, given names)"""
        if self.surname and self.given_names:
            surname_part = f"{self.tussenvoegsel} {self.surname}".strip() if self.tussenvoegsel else self.surname
            return f"{surname_part}, {self.given_names}"
        return self.full_name

    @property
    def all_marriages(self):
        """Get all marriages for this person"""
        return self.marriages_as_person1 + self.marriages_as_person2

    def __repr__(self):
        return f'<Person {self.display_name}>'


class Place(db.Model):
    """Model for geographic locations"""
    __tablename__ = 'places'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False, unique=True)
    country = db.Column(db.String(100))
    region = db.Column(db.String(100))
    coordinates = db.Column(db.String(100))  # lat,lng format
    description = db.Column(db.Text)
    historical_context = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    persons = db.relationship('Person', secondary=person_places, back_populates='places')
    events = db.relationship('Event', back_populates='place')

    def __repr__(self):
        return f'<Place {self.name}>'


class Event(db.Model):
    """Model for family events"""
    __tablename__ = 'events'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(255), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)  # birth, death, marriage, etc.
    date = db.Column(db.String(100))  # Flexible date format
    place_id = db.Column(UUID(), db.ForeignKey('places.id'))
    description = db.Column(db.Text)

    # Metadata
    extraction_chunk_id = db.Column(db.Integer)
    extraction_method = db.Column(db.String(50), default='llm')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    place = db.relationship('Place', back_populates='events')
    participants = db.relationship('Person', secondary=event_participants, back_populates='events')
    sources = db.relationship('Source', secondary='event_sources', back_populates='events')

    def __repr__(self):
        return f'<Event {self.title}>'


class Marriage(db.Model):
    """Model for marriage relationships"""
    __tablename__ = 'marriages'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    person1_id = db.Column(UUID(), db.ForeignKey('persons.id'), nullable=False)
    person2_id = db.Column(UUID(), db.ForeignKey('persons.id'), nullable=False)

    marriage_date = db.Column(db.String(100))
    marriage_place_id = db.Column(UUID(), db.ForeignKey('places.id'))
    divorce_date = db.Column(db.String(100))
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    person1 = db.relationship('Person', foreign_keys=[person1_id], back_populates='marriages_as_person1')
    person2 = db.relationship('Person', foreign_keys=[person2_id], back_populates='marriages_as_person2')
    marriage_place = db.relationship('Place', foreign_keys=[marriage_place_id])

    def __repr__(self):
        return f'<Marriage {self.person1_id} & {self.person2_id}>'


# Association table for family children
family_children = db.Table('family_children',
    db.Column('family_id', UUID(), db.ForeignKey('families.id'), primary_key=True),
    db.Column('person_id', UUID(), db.ForeignKey('persons.id'), primary_key=True)
)


class Family(db.Model):
    """Model for family units (parents + children)"""
    __tablename__ = 'families'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    family_identifier = db.Column(db.String(100))  # Like "III.2" from source text
    generation_number = db.Column(db.Integer)

    # Parents
    father_id = db.Column(UUID(), db.ForeignKey('persons.id'))
    mother_id = db.Column(UUID(), db.ForeignKey('persons.id'))

    # Marriage info
    marriage_date = db.Column(db.String(100))
    marriage_place_id = db.Column(UUID(), db.ForeignKey('places.id'))

    # Additional info
    notes = db.Column(db.Text)

    # Extraction metadata
    extraction_chunk_id = db.Column(db.Integer)
    extraction_method = db.Column(db.String(50), default='llm')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    father = db.relationship('Person', foreign_keys=[father_id], back_populates='families_as_father')
    mother = db.relationship('Person', foreign_keys=[mother_id], back_populates='families_as_mother')
    marriage_place = db.relationship('Place', foreign_keys=[marriage_place_id])
    children = db.relationship('Person', secondary=family_children, back_populates='families_as_child')

    def __repr__(self):
        return f'<Family {self.family_identifier or self.id}>'


class Occupation(db.Model):
    """Model for person occupations"""
    __tablename__ = 'occupations'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    person_id = db.Column(UUID(), db.ForeignKey('persons.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.String(100))
    end_date = db.Column(db.String(100))
    place_id = db.Column(UUID(), db.ForeignKey('places.id'))
    notes = db.Column(db.Text)

    # Relationships
    person = db.relationship('Person', back_populates='occupations')
    place = db.relationship('Place')

    def __repr__(self):
        return f'<Occupation {self.title}>'


# Association table for event sources
event_sources = db.Table('event_sources',
    db.Column('event_id', UUID(), db.ForeignKey('events.id'), primary_key=True),
    db.Column('source_id', UUID(), db.ForeignKey('sources.id'), primary_key=True)
)

# Association table for person sources
person_sources = db.Table('person_sources',
    db.Column('person_id', UUID(), db.ForeignKey('persons.id'), primary_key=True),
    db.Column('source_id', UUID(), db.ForeignKey('sources.id'), primary_key=True)
)


class Source(db.Model):
    """Model for genealogical sources"""
    __tablename__ = 'sources'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(100), nullable=False)  # book, document, website, etc.
    author = db.Column(db.String(255))
    publication_date = db.Column(db.String(100))
    location = db.Column(db.String(255))
    url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    confidence = db.Column(db.String(50))  # primary, secondary, etc.

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    events = db.relationship('Event', secondary=event_sources, back_populates='sources')
    persons = db.relationship('Person', secondary=person_sources)

    def __repr__(self):
        return f'<Source {self.title}>'


class JobFile(db.Model):
    """Model for storing uploaded files and job results"""
    __tablename__ = 'job_files'

    id = db.Column(UUID(), primary_key=True, default=uuid.uuid4)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)

    # Job information
    task_id = db.Column(db.String(36), nullable=False)  # Celery task ID
    job_type = db.Column(db.String(50), nullable=False)  # ocr, extraction, gedcom, research
    file_type = db.Column(db.String(20), nullable=False)  # input, output

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f'<JobFile {self.filename} ({self.job_type})>'
