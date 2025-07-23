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

## Development Phases Summary (2025)

### Completed Phases Overview ✅

**Phase 0-3: Infrastructure & Foundation** (January 2025)
- **Docker & Production Setup**: SSL automation, Celery workers, offline development
- **Code Cleanup**: Removed obsolete API blueprints, dataclass models, OpenAI integration, CLI commands
- **Configuration**: Centralized settings, fixed service instantiation, standardized naming
- **Database Migration**: OCR to database, RAG from database, system service updates

**Phase 4: Test Coverage Improvements** (July 2025) ✅ **COMPLETED**
- **All Target Modules**: 8/8 modules improved from low coverage to 85%+ comprehensive coverage
- **+206 New Tests**: Systematic test creation with fixture-based architecture
- **Quality Gates**: All tests passing, linting clean, pytest-celery integration
- **Technical Debt**: Test infrastructure fully stabilized and documented

## Current Focus: Feature Completion (July 2025)

**STATUS**: Infrastructure complete, ready for feature completion and UI polish

## Phase 5: Complete Halfway-Implemented Features

### Critical Issues Found (High Priority) 🔴

#### 1. **Research Question Generation - BROKEN**
**Status**: Core functionality complete but broken due to method name mismatch
- **Issue**: `research_tasks.py` calls `generator.generate_questions()` but class implements `generate_all_questions()`
- **Impact**: Research question feature completely non-functional
- **Fix**: One line change to align method names
- **Effort**: 5 minutes

#### 2. **Job Status Polling - MISSING**  
**Status**: Forms work but no real-time feedback
- **Missing**: 
  - `/api/jobs` endpoint returns empty data
  - `/api/jobs/<task_id>` endpoint for individual job status
  - Real-time job table updates (shows "No jobs found" always)
  - Progress tracking for OCR, GEDCOM, research (only extraction has it)
- **Current**: Job submission works but users get no feedback
- **Effort**: 2-3 days to implement complete job monitoring

#### 3. **RAG Query Interface - INCOMPLETE**
**Status**: Backend complete, frontend missing
- **Exists**: Full RAG service, database models, basic templates
- **Missing**:
  - Query input form on RAG page  
  - Query submission API endpoints
  - Search results display
  - Query session management UI
- **Current**: Can view corpus statistics but can't actually query
- **Effort**: 1-2 days for complete query interface

### Medium Priority Features 🟡

#### 4. **Research Questions Display Page**
- **Issue**: Generated research questions have nowhere to be displayed
- **Need**: Dedicated page to view and export research questions
- **Effort**: 1 day

#### 5. **Job Results Download**  
- **Issue**: Users can't download GEDCOM files or OCR results
- **Need**: Download links for completed jobs
- **Effort**: 0.5 days

#### 6. **Enhanced Progress Tracking**
- **Issue**: Limited progress updates for long-running tasks
- **Need**: More granular progress for OCR, extraction workflows
- **Effort**: 1 day

## Phase 6: UI Consolidation and Cleanup

### Architectural Issues (Medium Priority) 🟡

#### 1. **Dashboard Consolidation**
**Problem**: Two overlapping dashboards with unclear purposes
- **Current**: 
  - Main page (`/`) - has broken tool buttons
  - Tools page (`/tools`) - working tool forms
- **Solution**: Merge into single, coherent dashboard
- **Effort**: 1-2 days

#### 2. **Blueprint Organization**  
**Problem**: Functionality scattered across blueprints inconsistently
- **Issues**:
  - Main blueprint has non-functional tool buttons
  - Tools blueprint has working forms  
  - RAG blueprint partially complete
  - Entities blueprint separate (good)
- **Solution**: Reorganize with clear separation of concerns
- **Effort**: 1 day

#### 3. **JavaScript Cleanup**
**Problem**: Broken JavaScript references throughout templates
- **Issues**:
```javascript
// These functions don't exist:
onclick="runTool('ocr')"        // ❌ Broken  
onclick="runTool('research')"   // ❌ Broken
onclick="refreshStatus()"       // ❌ Broken

// Only this works:
onclick="runExtraction()"       // ✅ Works
```
- **Solution**: Implement missing functions or remove broken references
- **Effort**: 0.5 days

### Navigation and UX Issues 🟡

#### 4. **Consistent Navigation**
- **Problem**: Users get lost between different tool interfaces
- **Solution**: Unified navigation with clear workflow paths
- **Effort**: 1 day

#### 5. **Error Handling UI**
- **Problem**: Poor user feedback for errors and failures  
- **Solution**: Consistent error messages and user guidance
- **Effort**: 1 day

#### 6. **Mobile Responsiveness** 🟢
- **Current**: Basic Bootstrap responsive design
- **Enhancement**: Better mobile experience for tool forms
- **Effort**: 0.5 days

## Recommended Execution Order

### Quick Wins (1-2 days total):
1. **Fix research questions method name** (5 minutes)
2. **Remove broken JavaScript** (2 hours)  
3. **Add research questions display page** (4 hours)

### Core Features (1 week):
4. **Implement job status polling API** (2-3 days)
5. **Complete RAG query interface** (2 days)
6. **Add job results download** (0.5 days)

### UI Polish (3-4 days):
7. **Consolidate dashboards** (1-2 days)
8. **Reorganize blueprints** (1 day)
9. **Improve navigation and error handling** (1 day)

### Total Effort Estimate:
- **Phase 5**: ~1.5 weeks  
- **Phase 6**: ~1 week
- **Combined**: ~2.5 weeks for complete implementation

**Key Insight**: The project is very close to being fully functional - most issues are in the presentation layer rather than core business logic. The biggest impact would come from implementing job status polling, which would transform the user experience from "submit and hope" to real-time progress tracking.

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

## Technical Architecture Status (July 2025)

**Current Implementation:**
- **Core Business Logic**: Complete and tested (85%+ coverage across all modules)
- **Database Layer**: PostgreSQL with pgvector, full RAG capabilities, OCR storage
- **Background Processing**: Celery tasks for OCR, extraction, GEDCOM, research questions
- **Web Interface**: Flask blueprints with comprehensive test coverage
- **Testing Infrastructure**: 598 tests passing (100% pass rate) with pytest-flask integration

**Key Features Implemented:**
- ✅ **Database-Driven Prompts**: LLM prompts loaded from database with web management
- ✅ **OCR Pipeline**: PDF processing with database storage and progress tracking  
- ✅ **LLM Extraction**: Family-focused genealogy extraction with chunk processing
- ✅ **GEDCOM Generation**: Export to standard genealogy format
- ✅ **RAG System**: Text chunking, embeddings, semantic search backend
- ✅ **Entity Management**: Person/Family/Place browsing and management