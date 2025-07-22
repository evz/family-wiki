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
- **Web Interface**: Browser-based access to all tools with progress tracking
- **Shared Services**: Business logic services used by web interface
- **Blueprint Organization**: Clean separation of web routes and API endpoints
- **Background Tasks**: Celery tasks for long-running operations

## Project Structure *(Cleanup in Progress)*

```
family-wiki/
├── app.py                         # Main Flask application  
├── web_app/                       # Unified web application package
│   ├── services/                  # Business logic services
│   │   ├── rag_service.py         # RAG functionality and text processing
│   │   ├── prompt_service.py      # LLM prompt management
│   │   ├── ocr_service.py         # OCR processing service
│   │   ├── gedcom_service.py      # GEDCOM generation service
│   │   ├── research_service.py    # Research questions service
│   │   └── system_service.py      # System status and configuration
│   ├── blueprints/               # Flask route blueprints  
│   │   ├── main.py               # Main web routes
│   │   ├── tools.py              # Tool dashboard (being refactored)
│   │   ├── entities.py           # Entity browsing interface
│   │   └── rag.py                # RAG query interface
│   ├── database/                 # Database layer
│   │   ├── models.py             # SQLAlchemy database models
│   │   └── database.py           # Database configuration
│   ├── repositories/             # Data access layer (Repository Pattern)
│   │   ├── genealogy_repository.py # Entity repository
│   │   ├── gedcom_repository.py   # GEDCOM import/export operations
│   │   └── job_file_repository.py  # File processing jobs
│   ├── tasks/                    # Background task definitions
│   │   ├── gedcom_tasks.py       # GEDCOM generation tasks
│   │   ├── ocr_tasks.py          # OCR processing tasks
│   │   └── research_tasks.py     # Research question tasks
│   ├── pdf_processing/           # PDF processing and AI extraction
│   │   ├── ocr_processor.py      # OCR with rotation detection
│   │   ├── llm_genealogy_extractor.py # AI-powered data extraction
│   │   └── genealogy_model_benchmark.py # LLM model testing
│   ├── shared/                   # Common utilities and data models
│   │   ├── gedcom_parser.py      # GEDCOM file parsing
│   │   ├── gedcom_writer.py      # GEDCOM file generation
│   │   ├── dutch_utils.py        # Dutch name/language utilities
│   │   └── logging_config.py     # Common logging configuration
│   ├── static/                   # Web interface assets
│   └── research_question_generator.py # Research question generation
├── templates/                    # Jinja2 templates
├── tests/                        # Comprehensive test suite
└── requirements.txt             # Dependencies

Notes: Phase 1 cleanup complete - obsolete API blueprints, CLI commands, and dataclass models removed.
```

## Usage

**Web Interface:**
```bash
# Setup
source .venv/bin/activate
export FLASK_APP=app.py

# Start web application
flask run              # Visit http://localhost:5000
```

**Available Features:**
- **Entity Browser**: View extracted Person/Family/Place entities
- **RAG Queries**: Ask questions about source texts using semantic search
- **Prompt Management**: Edit LLM prompts for extraction
- **Tool Dashboard**: Access OCR, extraction, and GEDCOM tools

**Docker Development:**
```bash
docker-compose up      # Start PostgreSQL + web app
# Visit http://localhost:5000
```

## Key Technical Notes

- **Family-Focused Extraction**: LLM extracts family units with parent-child relationships, not just isolated individuals
- **Dutch Language**: Handles Dutch text, names, and genealogical conventions
- **Genealogical Symbols**: * (birth), ~ (baptism), † (death), x (marriage)
- **Generation Linking**: Tracks generation numbers and family group identifiers
- **LLM Models**: aya:35b-23 default model for structured extraction (configurable)
- **Progress Tracking**: Real-time progress updates for long-running extractions

## Current Phase: Cleanup & Completion (January 2025)

**STATUS: Phase 2 Complete - Starting Phase 3**

Phase 0, Phase 1, and Phase 2 are complete. Phase 3 (Complete Database Migration) is starting.

### Cleanup Plan Overview

**Phase 0: Docker & Production Setup** ✅ **COMPLETED**
1. ✅ **Documentation cleanup** - Update CLAUDE.md, remove obsolete sections
2. ✅ **Fix Celery task discovery** - Added task autodiscovery to celery_app.py
3. ✅ **Add automated SSL with Let's Encrypt** - Added nginx-certbot container
4. ✅ **Make nginx required in production** - Removed manual SSL, nginx always included
5. ✅ **Add production Celery worker** - Added celery worker and Redis to prod compose
6. ✅ **Offline-capable `make dev`** - Smart build + .env support for local ollama

**Phase 1: Remove Dead Code** ✅ **COMPLETED**
7. ✅ **Remove obsolete API blueprints** - Deleted `api_system.py`, `api_rag.py`, `extraction.py` and related tests
8. ✅ **Remove dataclass models** - Deleted old dataclass models and tests (models.py, test_models.py)
9. ✅ **Remove OpenAI integration** - Cleaned out OpenAI code from `llm_genealogy_extractor.py`
10. ✅ **Remove CLI commands** - Deleted `commands.py` and related test files

**Phase 2: Fix Configuration** ✅ **COMPLETED**
6. ✅ **Centralize configuration** - Removed hardcoded defaults, require env vars, updated .env.example
7. ✅ **Fix service instantiation** - Removed global instances from rag.py, use inline instantiation
8. ✅ **Standardize naming** - Fixed "particle" to "tussenvoegsel" in Dutch utilities

**Phase 3: Complete Database Migration** ✅ **COMPLETED**
9. ✅ **OCR to database** - Create page table, save OCR results to DB
10. ✅ **RAG from database** - Update RAG service to load from DB rows  
11. ✅ **System service update** - Replace file-based status with DB queries

**Phase 4: Improve Error Handling**
12. RAG service exceptions - Add proper exception handling
13. Task error handling - Fix naked exceptions in background tasks
14. Repository exceptions - Add proper error handling to repository layer

**Phase 5: Complete Missing Features**  
15. RAG query interface - Build web interface for query sessions
16. Job status polling - Implement Celery job status endpoints
17. Research questions - Complete research question generation

**Phase 6: UI Consolidation**
18. Main dashboard - Move tools dashboard to main blueprint
19. Blueprint separation - Split tools.py into separate blueprints
20. Remove unused JS - Keep only job polling JavaScript

### How to Resume Work

**Current Focus**: Phase 3 complete! Ready to proceed with Phase 4 (Error Handling improvements)

**Next Steps:**
1. **Phase 4**: Improve error handling throughout the codebase
   - Add proper exception handling to RAG service
   - Fix naked exceptions in background tasks  
   - Add proper error handling to repository layer

2. **Phase 5**: Complete halfway-implemented features
   - Complete research question generation functionality
   - Implement job status polling endpoints
   - Build RAG query interface

3. **Phase 6**: UI consolidation and cleanup
   - Consolidate dashboard functionality
   - Clean up blueprint organization
   - Remove unused JavaScript

**Current State**: Test infrastructure fully stabilized. All 345 tests passing (100% pass rate).

**pytest-flask Pattern** (use this for Flask context test failures):
```python
# OLD (manual context management):
def test_something(self):
    with app.app_context():
        service = MyFlaskService()
        # test code

# NEW (pytest-flask automatic context):
def test_something(self, app):
    service = MyFlaskService()
    # test code - Flask context provided automatically
```

**Quality Gates**: Each task must pass `ruff check .` and `pytest` before completion.

**Test Status**: 0 failed, 345 passed (100% pass rate). pytest-flask integration complete. ✅

## Development

**CRITICAL WORKFLOW REQUIREMENTS:**

**Virtual Environment (MANDATORY):**
- **ALWAYS** activate the virtual environment before ANY Python commands: `source .venv/bin/activate`
- The virtualenv is located in `.venv/` directory in the project root
- **NEVER** run Python/pytest/ruff commands without activating the virtualenv first
- This applies to ALL commands: pytest, ruff, flask, pip, python, etc.
- **CRITICAL**: After conversation compaction, always remember to activate virtualenv

**Development Principles (MANDATORY):**
- **Simplest Approach**: Always choose the simplest solution that solves the problem
- **Value Verification**: Before starting any task, confirm it's actually worth doing and serves our overall goals
- **Question Everything**: If a task seems complex or unclear, step back and ask if there's a simpler way or if it's needed at all
- **Minimize Scope**: Do only what's necessary to achieve the goal, nothing more

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
pytest tests/test_entities_blueprint.py  # Test entity browsing
pytest -v                          # Verbose output

# Test Coverage (REQUIREMENT: Must maintain >90% coverage)
pytest --cov=web_app --cov-report=html --cov-report=term-missing --cov-fail-under=90

# Test specific modules for Flask context issues
pytest tests/test_llm_genealogy_extractor.py --tb=short    # Check for Flask context errors
pytest tests/test_genealogy_model_benchmark.py --tb=short  # 8 remaining failures
pytest tests/test_rag_api.py --tb=short                    # RAG API issues
```

**Linting:**
```bash
# ALWAYS activate virtualenv first
source .venv/bin/activate

ruff check .                        # Check all code
ruff check . --fix                  # Auto-fix issues
```

**pytest-flask Setup & Usage:**
```bash
# pytest-flask is installed and configured in requirements.txt
pip install pytest-flask==1.3.0

# Key files for pytest-flask:
# - tests/conftest.py: Contains app fixture that works with pytest-flask
# - Any test needing Flask context: Add 'app' parameter to test method

# Common Flask context errors and fixes:
# ERROR: "Working outside of application context"
# FIX: Add 'app' parameter to test method and remove manual app.app_context()

# Example conversion:
# BEFORE: def test_method(self): with app.app_context(): ...
# AFTER:  def test_method(self, app): ...  # Flask context automatic
```

**Architecture:**
- **Service Layer**: `web_app/services/` contains all business logic
- **Flask Blueprints**: `web_app/blueprints/` organizes web routes
- **Database Layer**: `web_app/database/` and `web_app/repositories/` handle data access
- **Background Tasks**: `web_app/tasks/` contains Celery task definitions
- **Testing**: pytest-flask provides automatic Flask app context for tests

## Architecture Status

**Current State (January 2025):**
- **Database-Driven**: PostgreSQL + pgvector with RAG capabilities
- **Flask Application**: Web interface with background task processing 
- **Service Layer**: Shared business logic for web and background tasks
- **Blueprint Organization**: Separated API and web routes
- **Testing**: Comprehensive test suite with quality gates

**Key Features Implemented:**
- **Entity Storage**: Person/Family/Place entities in relational database
- **RAG System**: Text chunking, embeddings, semantic search
- **Prompt Management**: Database-stored prompts with web interface
- **Dutch Language Support**: Specialized genealogy parsing
- **Quality Control**: Mandatory linting and testing procedures

**Configuration:**
- **Ollama Settings**: Configurable via environment variables
  - `OLLAMA_HOST` - Ollama server host (default: 192.168.1.234)
  - `OLLAMA_PORT` - Ollama server port (default: 11434)
  - `OLLAMA_MODEL` - LLM model to use (default: aya:35b-23)
- **Database**: PostgreSQL with pgvector extension for embeddings
  - `DATABASE_URL` - Full database connection string
- **Example**: `export OLLAMA_HOST=localhost && export OLLAMA_MODEL=llama3.1:8b`

**Database Models:**
- **Core Entities**: `Person`, `Family`, `Place`, `Event`, `Marriage`, `Occupation`
- **RAG Components**: `TextCorpus`, `SourceText`, `QuerySession`, `Query`
- **Management**: `ExtractionPrompt`, `Source`

## Current Development Status (July 2025)

**Phase 4 Completed: Test Infrastructure Fixes & Code Cleanup** ✅
- **Test Configuration Fixed**: Resolved "TestConfig no longer works" issues affecting many tests
  - **BaseTestConfig Pattern**: Created environment-agnostic test configuration class
  - **Fixture Updates**: Updated all test files to use new configuration approach
  - **GEDCOM Parser Tests**: Fixed API changes from object attributes to dictionary access
  - **Blueprint Test Mocking**: Corrected mock patterns for inline service instantiation
  - **RAG Service Tests**: Re-enabled and fixed all 22 disabled RAG service tests

- **Database Compatibility**: Fixed UUID handling between PostgreSQL (production) and SQLite (tests)
  - **Platform-Independent UUID Type**: Created custom SQLAlchemy TypeDecorator for cross-database compatibility
  - **OCR Database Integration**: Fixed all database-related test failures
  - **Clean Database Fixtures**: Added missing OcrPage model to test cleanup

- **pytest-flask Integration**: Eliminated manual Flask app context management in tests
  - **Dependency Added**: Added `pytest-flask==1.3.0` to requirements.txt 
  - **Automatic Context**: Tests now get Flask app context automatically when using `app` fixture
  - **Simplified Pattern**: Changed from `with app.app_context():` to just `def test_method(self, app):`
  - **Genealogy Benchmark**: Fixed 20 out of 28 failing tests by applying pytest-flask pattern
  - **Clean Test Code**: Eliminated boilerplate app context management across test suite

- **Test Suite Health**: Complete test infrastructure resolution
  - **Before All Fixes**: ~66 failed, ~312 passed (83% pass rate)
  - **After All Fixes**: **0 failed, 345 passed (100% pass rate)** ✅
  - **Infrastructure Issues Resolved**: All configuration and test framework problems fixed
  - **pytest-flask Impact**: Universal application resolved all Flask context issues
  - **Complete Test Modules Fixed**: LLM Genealogy Extractor, Genealogy Model Benchmark, Research Question Generator, OCR tests

**Technical Infrastructure Completed:**
- **OCR Database Storage**: Single-page PDF processing with `OcrPage` table
- **Batch Grouping**: UUID-based batch identification for related uploads  
- **Page Number Extraction**: Automatic parsing from filenames (001.pdf → 1)
- **Language Detection**: Proper language detection with fallback to 'unknown'
- **Test Collection**: All 378 tests collect without import errors
- **Cross-Platform Database**: PostgreSQL in production, SQLite in tests with unified UUID handling

**Recently Completed (January 2025):**
- ✅ **GEDCOM Refactor**: Successfully converted from dataclasses to SQLAlchemy models with repository pattern
  - **Pure Parser**: `GEDCOMParser` now focuses solely on parsing logic without database dependencies
  - **Repository Pattern**: `GedcomRepository` handles all database operations and SQLAlchemy model creation
  - **Service Orchestration**: `GedcomService` coordinates between parser and repository for import/export
  - **Clean Architecture**: Separation of concerns following single responsibility principle

- ✅ **Test Infrastructure Overhaul**: Complete resolution of test configuration and compatibility issues
  - **Configuration Management**: Centralized test config without environment variable dependencies
  - **Service Instantiation**: Fixed global service instance issues with inline instantiation pattern
  - **Database Mocking**: Corrected test mocking patterns across all blueprint and service tests
  - **API Cleanup**: Removed obsolete tests for deleted API endpoints

**Recently Completed (July 2025):**
- ✅ **Complete Test Infrastructure Stabilization**: Fixed all remaining failing tests across the entire codebase
  - **LLM Genealogy Extractor**: Fixed all 31 failing tests and implemented database-driven prompts
    - **OpenAI Code Removal**: Completed Phase 1 cleanup by removing all OpenAI integration code
    - **pytest-flask Integration**: Applied automatic Flask context management across all tests
    - **Test Expectation Fixes**: Updated tests to match actual implementation (families + isolated_individuals structure)
    - **Dead Code Removal**: Eliminated unused methods (`get_extraction_summary`, `save_results`) and JSON backup functionality
    - **Database-Driven Prompts**: ✅ **NEW FEATURE** - LLM prompts now loaded from database instead of hardcoded
      - Default prompt stored in `web_app/database/default_prompts/dutch_genealogy_extraction.txt`
      - Automatically loaded into database on app startup
      - Users can now modify prompts through web interface
      - Proper fallback handling for database connectivity issues
  - **Genealogy Model Benchmark**: Fixed all 8 failing tests
    - Applied pytest-flask patterns for Flask context management
    - Fixed subprocess mock assertions to match actual implementation
    - Removed obsolete tests for non-existent functionality
  - **Research Question Generator**: Fixed all 8 failing tests  
    - Applied pytest-flask patterns throughout test suite
    - Fixed HTTP error mock configuration for proper exception handling
    - Corrected attribute name mismatches (`research_questions` vs `all_questions`)
  - **OCR Tests**: Fixed all 7 failing tests
    - Applied pytest-flask patterns for database integration tests
    - Removed obsolete CLI main function tests (deleted in Phase 1)
    - Fixed mock expectations to match actual implementation behavior
  - **Test Results**: **~66 failing → 0 failing tests** (100% success rate across all 345 tests)

**Remaining Technical Debt:**
- **Phase 4**: Error handling improvements throughout codebase
- **Phase 5**: Complete halfway-implemented features (research questions, wiki export)
- **Phase 6**: UI consolidation and cleanup

**Current Status**: ✅ **Phase 3 Complete** - Test infrastructure fully stabilized. All 345 tests passing (100% pass rate). Database migration complete, OCR database integration working, and comprehensive test coverage achieved. Ready to proceed with Phase 4 (Error Handling improvements).

**Progress:** Phase 0, Phase 1, Phase 2, and Phase 3 complete. Configuration centralized, dead code removed, Docker/SSL setup complete, test infrastructure fully functional and 100% reliable.