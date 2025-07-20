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
│   ├── repositories/             # Data access layer
│   │   ├── genealogy_repository.py # Entity repository
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

**Phase 3: Complete Database Migration**
9. OCR to database - Create page table, save OCR results to DB
10. RAG from database - Update RAG service to load from DB rows
11. System service update - Replace file-based status with DB queries

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

**Current Task**: OCR to database (Phase 3, Task 1)

**To get started:**
1. Create database table for storing OCR page results
2. Update OCR processor to save results to database instead of files
3. Update services that read OCR data to use database queries
4. Temporarily fix GEDCOM import issues that prevent app startup

**Quality Gates**: Each task must pass `ruff check .` and `pytest` before completion.

**Next Task**: RAG from database - Update RAG service to load from DB rows

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
- **Database Layer**: `web_app/database/` and `web_app/repositories/` handle data access
- **Background Tasks**: `web_app/tasks/` contains Celery task definitions

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

**Remaining Technical Debt:**
Per TODO.md analysis, remaining issues after Phase 2 cleanup:
- Incomplete database migration (OCR still saves to files) - **Phase 3 in progress**
- Poor error handling throughout codebase - **Phase 4 pending**
- Halfway-implemented features (research questions, wiki export) - **Phase 5 pending**

**Progress:** Phase 0, Phase 1, and Phase 2 complete. Configuration centralized, dead code removed, Docker/SSL setup complete.