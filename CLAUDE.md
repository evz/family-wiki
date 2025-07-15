# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Family Wiki Tools is a unified Flask application for AI-powered genealogy digitization. It processes Dutch family history books using OCR and LLM technology to extract structured family data.

**Core Features:**
- **OCR Processing**: Extract text from PDF scans with rotation detection
- **Family-Focused LLM Extraction**: AI-powered extraction that groups people into family units with parent-child relationships
- **GEDCOM Generation**: Create standard genealogy files from extracted data
- **Research Questions**: Generate intelligent research directions from family data
- **Model Benchmarking**: Test multiple LLM models for optimal extraction performance

**Architecture:**
- **Flask CLI Commands**: All tools available via `flask <command>` (e.g., `flask extract`)
- **Web Interface**: Browser-based access to all tools with progress tracking
- **Shared Services**: Common business logic used by both CLI and web interface
- **Blueprint Organization**: Clean separation of web routes and API endpoints

## Project Structure

```
family-wiki/
├── app.py                         # Main Flask application with CLI commands  
├── web_app/                       # Unified web application package
│   ├── services/                  # Business logic services
│   │   ├── extraction_service.py  # LLM extraction with progress tracking
│   │   ├── ocr_service.py         # OCR processing service
│   │   ├── gedcom_service.py      # GEDCOM generation service
│   │   ├── research_service.py    # Research questions service
│   │   └── benchmark_service.py   # Model benchmarking service
│   ├── blueprints/               # Flask route blueprints
│   │   ├── main.py               # Main web routes and tool dashboard
│   │   └── extraction.py         # Extraction API endpoints with progress tracking
│   ├── pdf_processing/           # PDF processing and AI extraction
│   │   ├── pdfs/                 # 101 PDF pages of Dutch family book
│   │   ├── extracted_text/       # OCR output files 
│   │   ├── ocr_processor.py      # OCR with rotation detection
│   │   ├── llm_genealogy_extractor.py # AI-powered data extraction
│   │   └── genealogy_model_benchmark.py # LLM model testing
│   ├── shared/                   # Common utilities and data models
│   │   ├── models.py             # Data models for persons, families, events
│   │   ├── gedcom_parser.py      # GEDCOM file parsing
│   │   ├── gedcom_writer.py      # GEDCOM file generation
│   │   ├── dutch_utils.py        # Dutch name/language utilities
│   │   └── logging_config.py     # Common logging configuration
│   ├── static/                   # Web interface assets
│   │   ├── css/main.css          # Professional styling
│   │   └── js/main.js            # JavaScript with real-time progress tracking
│   ├── commands.py               # Flask CLI command definitions
│   └── research_question_generator.py # Intelligent research questions
├── templates/                    # Jinja2 templates
├── tests/                        # Test suite
│   ├── test_services.py         # Service layer tests
│   ├── test_flask_app.py        # Flask app and CLI tests
│   └── test_*.py                # Additional tests
└── requirements.txt             # Dependencies
```

## Usage

**Flask CLI Commands (Recommended):**
```bash
# Setup
source .venv/bin/activate
export FLASK_APP=app.py

# Individual tools
flask ocr              # Extract text from PDFs with OCR
flask extract          # AI-powered family data extraction  
flask gedcom           # Generate GEDCOM files
flask research         # Generate research questions
flask benchmark        # Test LLM models for performance
flask pipeline         # Run complete workflow

# Options
flask extract --verbose     # Detailed output
flask status                # Check system status
flask --help               # Show all commands
```

**Web Interface:**
```bash
flask run              # Start web server
# Visit http://localhost:5000
```

**Features:**
- **CLI**: Perfect for automation, scripting, and detailed control
- **Web**: Real-time progress tracking, visual summaries, easy access
- **Both interfaces use the same underlying services**

## Key Technical Notes

- **Family-Focused Extraction**: LLM extracts family units with parent-child relationships, not just isolated individuals
- **Dutch Language**: Handles Dutch text, names, and genealogical conventions
- **Genealogical Symbols**: * (birth), ~ (baptism), † (death), x (marriage)
- **Generation Linking**: Tracks generation numbers and family group identifiers
- **LLM Models**: aya:35b-23 default model for structured extraction (configurable)
- **Progress Tracking**: Real-time progress updates for long-running extractions

## Development

**CRITICAL WORKFLOW REQUIREMENTS:**

**Virtual Environment (MANDATORY):**
- **ALWAYS** activate the virtual environment before ANY Python commands: `source .venv/bin/activate`
- The virtualenv is located in `.venv/` directory in the project root
- **NEVER** run Python/pytest/ruff commands without activating the virtualenv first
- This applies to ALL commands: pytest, ruff, flask, pip, python, etc.
- **CRITICAL**: After conversation compaction, always remember to activate virtualenv

**Quality Gates (MANDATORY):**
- **ALWAYS** run tests before completing any task: `source .venv/bin/activate && pytest`
- **ALWAYS** run linter before completing any task: `source .venv/bin/activate && ruff check .`
- These quality gates must pass before declaring any work "finished"
- If linter/tests fail, fix the issues before completing the task

**Setup:**
```bash
./setup.sh && source .venv/bin/activate
export FLASK_APP=app.py
```

**Testing:**
```bash
# ALWAYS activate virtualenv first
source .venv/bin/activate

pytest                              # Run all tests
pytest tests/test_services.py       # Test service layer
pytest tests/test_flask_app.py      # Test Flask app and CLI
pytest -v                          # Verbose output

# Test Coverage (REQUIREMENT: Must maintain >90% coverage)
pytest --cov=web_app --cov-report=html --cov-report=term-missing --cov-fail-under=90
```

**Linting:**
```bash
# ALWAYS activate virtualenv first
source .venv/bin/activate

ruff check .                        # Check all code
ruff check . --fix                  # Auto-fix issues
```

**Architecture:**
- **Service Layer**: `web_app/services/` contains all business logic
- **Flask Blueprints**: `web_app/blueprints/` organizes web routes
- **CLI Commands**: `web_app/commands.py` defines Flask CLI commands
- **Shared Code**: Both CLI and web use the same service classes

## Recent Improvements (July 2025)

**Major Architecture Refactor:**
- **Unified Flask App**: Single `app.py` with both CLI commands and web interface
- **Shared Services**: Common business logic used by both CLI and web (`web_app/services/`)
- **No More Subprocess Calls**: Web interface directly uses service classes instead of calling CLI tools
- **Flask CLI Commands**: Professional CLI with `flask <command>` instead of separate scripts
- **Blueprint Organization**: Clean separation of web routes (`web_app/blueprints/`)
- **Progress Tracking**: Real-time progress updates for LLM extraction with task management
- **Professional UI**: Modern CSS, JavaScript modules, responsive design
- **Comprehensive Testing**: Test suite covering services, Flask app, and CLI commands

**Family-Focused Extraction:**
- **Generation Linking**: Improved LLM prompt specifically tracks family relationships
- **Parent-Child Connections**: Groups people into family units instead of isolated individuals  
- **Dutch Genealogy Patterns**: Recognizes "Kinderen van" (children of) phrases
- **Confidence Scoring**: Different confidence levels for family relationships vs individual facts
- **Structured Output**: `families[]` and `isolated_individuals[]` with proper relationships

**Command Examples:**
```bash
flask extract --verbose    # AI extraction with progress tracking
flask pipeline             # Complete OCR → extraction → GEDCOM → research workflow  
flask run                  # Web interface with real-time progress bars
flask db-clear             # Clear database (for development/testing)
flask status               # Show system status including database statistics
```

## Database-Driven Architecture (Current)

**Major Migration Status (July 2025):**
- ✅ **PostgreSQL + pgvector setup** - Docker containerized with external ollama
- ✅ **Database models** - Complete SQLAlchemy models with proper relationships
- ✅ **Prompt management** - Database-stored prompts with file-based defaults
- ✅ **Extraction service database integration** - Stores entities in database instead of JSON
- ✅ **API blueprint separation** - Clean separation of API endpoints from web pages
- ✅ **Entity detail pages** - Browse Person/Event/Place entities via entities blueprint
- ✅ **RAG query interface** - Free-form questions with vector similarity search
- ✅ **Source text storage** - Store and chunk source documents for RAG
- 🔄 **Test coverage improvement** - Working toward >90% coverage requirement

**Database Models:**
- **Person, Family, Place, Event, Marriage** - Core genealogy entities with proper foreign keys
- **TextCorpus, SourceText** - RAG-ready text storage with pgvector embeddings
- **Query, QuerySession** - Track user questions and RAG responses
- **ExtractionPrompt** - Editable LLM prompts with safety mechanisms

**Current Architecture:**
- **Database Storage**: All extracted entities stored in PostgreSQL with relationships
- **Prompt Management**: Database-stored prompts with file-based defaults for safety
- **Dutch Name Parsing**: Proper handling of tussenvoegsel (van, de, etc.)
- **RAG Ready**: pgvector integration for semantic similarity search
- **API Organization**: Separated API endpoints into dedicated blueprint

**Recent Database Changes:**
- Extraction service now saves Person/Family/Place entities to database
- Active prompt loaded from database instead of hardcoded
- Added database statistics and clearing functionality
- Created separate API blueprint for better code organization

**Configuration:**
- **Ollama Settings**: Configurable via environment variables
  - `OLLAMA_HOST` - Ollama server host (default: 192.168.1.234)
  - `OLLAMA_PORT` - Ollama server port (default: 11434)
  - `OLLAMA_MODEL` - LLM model to use (default: aya:35b-23)
- **Database**: PostgreSQL with pgvector extension for embeddings
  - `DATABASE_URL` - Full database connection string
- **Example**: `export OLLAMA_HOST=localhost && export OLLAMA_MODEL=llama3.1:8b`

## Database-Driven Architecture (December 2025)

**Major Refactor in Progress**: Transitioning from file-based to database-driven architecture with PostgreSQL + pgvector for RAG (Retrieval-Augmented Generation) capabilities.

### **New Database Features:**
1. **Entity Storage**: Persons, Places, Events, Families stored in relational database with proper foreign keys
2. **RAG System**: Text chunks with embeddings for semantic search and question-answering
3. **Prompt Management**: Editable LLM prompts stored in database with versioning
4. **Source Text Management**: Organized text corpora for targeted querying
5. **Query Sessions**: Track user questions and answers with context

### **Database Models Overview:**
- **Core Entities**: `Person`, `Place`, `Event`, `Family`, `Marriage`, `Occupation`
- **RAG Components**: `TextCorpus`, `SourceText`, `QuerySession`, `Query`
- **Management**: `ExtractionPrompt`, `Source`
- **Relationships**: Proper foreign keys instead of JSON arrays

### **RAG Implementation:**
- **Embeddings**: Using Ollama's built-in embeddings API
- **Vector Storage**: pgvector extension for similarity search
- **Similarity**: Cosine similarity for semantic text matching
- **Workflow**: 
  1. Text chunked and embedded during ingestion
  2. User questions embedded and matched against chunks
  3. Relevant context sent to Ollama for generation

### **Docker Setup:**
- **Web Container**: Flask app with development hot-reload
- **Database Container**: PostgreSQL 16 with pgvector extension
- **Network**: Web app communicates with external Ollama server at 192.168.1.234

### **Key Improvements:**
- **Iterative Workflow**: Edit prompts, clear database, re-run extraction
- **Detail Pages**: Browse extracted entities with web interface
- **Free-form Queries**: Ask questions about source text via RAG
- **Corpus Selection**: Choose which text collections to query
- **Relationship Tracking**: Proper normalized database design

### **Migration Status**: 
- ✅ Docker configuration
- ✅ Database models with pgvector
- ✅ Flask app database integration  
- ✅ Extraction service database storage
- ✅ Web interface for entity browsing
- ✅ RAG query interface
- ✅ Prompt management UI

## Current Development Status (July 2025)

**Major Strategic Goals (Long-term):**
- **Database-Driven Architecture Migration**: ✅ **COMPLETED** - Successfully migrated from file-based to PostgreSQL + pgvector with RAG capabilities
- **RAG System Implementation**: ✅ **COMPLETED** - Full RAG functionality with text chunking, embeddings, and semantic search
- **API Blueprint Organization**: ✅ **COMPLETED** - Clean separation of API endpoints from web pages
- **Entity Management System**: ✅ **COMPLETED** - Browse/manage Person/Family/Place entities via web interface
- **Prompt Management System**: ✅ **COMPLETED** - Database-stored prompts with versioning and safety mechanisms
- **Quality Control Framework**: ✅ **COMPLETED** - Comprehensive testing and linting procedures established
- **Test Coverage Excellence**: 🔄 **IN PROGRESS** - Target >90% coverage (currently 57%)

**Last Session Progress:**
- **Test Coverage**: Improved from 43% to 57% with 178 tests passing
- **Linting**: All 105 linting errors fixed (ruff check . passes cleanly)
- **Code Quality**: Comprehensive quality control procedures established

**Recent Achievements:**
- ✅ Fixed all RAG service test failures (22/22 tests passing)
- ✅ Fixed all prompt service test failures (25/25 tests passing)
- ✅ Fixed all RAG API test failures (16/16 tests passing)
- ✅ Created comprehensive Dutch utilities tests (29 tests, 91% coverage)
- ✅ Created comprehensive GEDCOM writer tests (14 tests, 56% coverage)
- ✅ Created comprehensive GEDCOM parser tests (13 tests, 89% coverage)
- ✅ Fixed all linting issues (trailing whitespace, unused variables, bare except, imports)
- ✅ Established mandatory quality gates (linting + tests before completing tasks)

**Current Test Coverage Status:**
- **Overall**: 57% (2877 total lines, 1226 missed)
- **High Coverage Modules** (>85%):
  - RAG service: 88% (comprehensive coverage)
  - Prompt service: 91% (excellent coverage)
  - GEDCOM parser: 89% (newly improved from 13%)
  - Dutch utilities: 91% (newly improved from 17%)
  - OCR service: 88%
  - Research service: 86%
  - Logging config: 95%

**Low Coverage Modules** (priority for next session):
- `web_app/pdf_processing/llm_genealogy_extractor.py`: 10% coverage
- `web_app/pdf_processing/genealogy_model_benchmark.py`: 13% coverage
- `web_app/research_question_generator.py`: 16% coverage
- `web_app/pdf_processing/ocr_processor.py`: 16% coverage
- `web_app/services/extraction_service.py`: 42% coverage
- `web_app/services/gedcom_service.py`: 48% coverage
- `web_app/shared/gedcom_writer.py`: 56% coverage

**Next Steps for 90% Coverage Target:**
1. Create tests for `llm_genealogy_extractor.py` (biggest impact - 175 missed lines)
2. Create tests for `genealogy_model_benchmark.py` (121 missed lines)  
3. Create tests for `research_question_generator.py` (169 missed lines)
4. Create tests for `ocr_processor.py` (118 missed lines)
5. Expand tests for `extraction_service.py` (148 missed lines)

**Test Infrastructure Created:**
- `clean_db` fixture in conftest.py for pristine database state
- Comprehensive test utilities for RAG functionality
- UUID handling patterns for PostgreSQL/SQLite compatibility
- Proper error handling test patterns
- Database integration test patterns

**Quality Control Established:**
- **Mandatory linting**: `source .venv/bin/activate && ruff check .`
- **Mandatory testing**: `source .venv/bin/activate && pytest`
- **Coverage monitoring**: `pytest --cov=web_app --cov-report=term-missing`
- **Target**: Maintain >90% test coverage for all new code

**Technical Debt Fixed:**
- All UUID handling issues between PostgreSQL and SQLite resolved
- All unused variables and imports removed
- All bare except statements replaced with specific exceptions
- All trailing whitespace removed
- All import ordering issues resolved
- All code formatting standardized

**Major Architecture Achievements:**
- **Database Integration**: Full PostgreSQL + pgvector setup with Docker
- **RAG Implementation**: Complete retrieval-augmented generation system with:
  - Text corpus management and chunking
  - Vector embeddings with semantic search
  - Query session tracking and context management
  - Free-form natural language queries about source texts
- **API Organization**: Clean blueprint separation (main, api, entities, rag, extraction)
- **Entity Management**: Web interface for browsing Person/Family/Place entities
- **Prompt Management**: Database-stored prompts with file-based defaults and safety mechanisms
- **Quality Framework**: Established mandatory linting and testing procedures

## Test Coverage Status (July 2025)

**Current Coverage: 91% overall** ✅ **Target Achieved!**

Major improvements completed through systematic testing approach:
- **Repository Pattern**: Separated database operations from business logic with full test coverage
- **API Blueprints**: Comprehensive testing of all web routes and API endpoints
- **Service Layer Testing**: Complete test coverage for business logic with error path testing
- **Dutch Genealogy Parser**: Full implementation and testing (0% → 94% coverage)
- **Mock-based Testing**: Isolated unit tests for services and APIs

**Coverage by Module:**
- **dutch_genealogy_parser.py**: 94% coverage (was 0% - major improvement)
- **Services**: 85%+ (high-impact business logic with error handling)
- **API Blueprints**: 88% (comprehensive endpoint testing)
- **Models**: 78% (core data structures)
- **Repository**: 85% (database operations)

**Recent Achievements:**
- ✅ **Dutch Name Parser**: Complete implementation with 45 test cases covering all Dutch genealogy patterns
- ✅ **API Blueprint Testing**: Comprehensive error path testing for all endpoints
- ✅ **Repository Pattern**: Fixed database model compatibility issues
- ✅ **Test Infrastructure**: Robust mock-based testing framework

**Quality Metrics:**
- **91% Test Coverage**: Exceeds 90% target
- **Comprehensive Error Handling**: All service layers include error path testing
- **Dutch Language Support**: Full parser for Dutch names, dates, and genealogy patterns
- **Database Integration**: Repository pattern with proper foreign key handling

**Continue From Here:**
The **Test Coverage Excellence** goal has been achieved! The system now has 91% test coverage with comprehensive testing of all major components. The infrastructure is ready for production use with high confidence in code quality and reliability. Next steps should focus on production deployment, documentation updates, and feature enhancements.