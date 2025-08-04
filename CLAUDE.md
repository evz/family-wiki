# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Family Wiki Tools is a Flask application for AI-powered genealogy digitization. It processes Dutch family history books using OCR and LLM technology to extract structured family data.

**Core Features:**
- **OCR Processing**: Extract text from PDF scans with rotation detection
- **Family-Focused LLM Extraction**: AI-powered extraction that groups people into family units with parent-child relationships
- **GEDCOM Generation**: Create standard genealogy files from extracted data
- **Research Questions**: Generate intelligent research directions from family data
- **RAG System**: Semantic search and question-answering over source texts
- **Model Benchmarking**: Test multiple LLM models for optimal extraction performance

**Architecture:**
- **Web Interface**: Browser-based access to all tools with progress tracking
- **Service Layer**: Business logic services with proper dependency injection
- **Repository Pattern**: Data access layer with base classes and error handling
- **Background Tasks**: Celery tasks for long-running operations
- **Modular Blueprints**: Clean separation of web routes by functionality

## Project Structure

```
family-wiki/
├── web_app/                       # Main Flask application package
│   ├── __init__.py                # Flask app factory and configuration
│   ├── services/                  # Business logic services (7 services)
│   │   ├── rag_service.py         # RAG functionality and semantic search
│   │   ├── prompt_service.py      # LLM prompt management
│   │   ├── gedcom_service.py      # GEDCOM generation service
│   │   ├── system_service.py      # System status and embedding models
│   │   ├── text_processing_service.py # Text chunking and processing
│   │   └── exceptions.py          # Service layer exceptions
│   ├── repositories/              # Data access layer (Repository Pattern)
│   │   ├── base_repository.py     # Base repository with error handling
│   │   ├── genealogy_base_repository.py # Shared genealogy operations
│   │   ├── genealogy_repository.py # Person/Family/Place entities
│   │   ├── gedcom_repository.py   # GEDCOM import/export operations
│   │   ├── job_file_repository.py # File processing jobs
│   │   ├── ocr_repository.py      # OCR operation storage
│   │   └── rag_repository.py      # RAG corpus and query management
│   ├── blueprints/               # Flask route blueprints (modular)
│   │   ├── main.py               # Main dashboard and navigation
│   │   ├── entities.py           # Entity browsing interface
│   │   ├── prompts.py            # Prompt management interface
│   │   ├── rag.py                # RAG corpus management
│   │   ├── ocr.py                # OCR processing forms
│   │   ├── extraction.py         # LLM extraction interface
│   │   ├── gedcom.py             # GEDCOM generation
│   │   ├── research.py           # Research questions
│   │   └── jobs.py               # Job status and management
│   ├── tasks/                    # Background task definitions
│   │   ├── ocr_tasks.py          # OCR processing tasks
│   │   ├── extraction_tasks.py   # LLM extraction tasks
│   │   ├── gedcom_tasks.py       # GEDCOM generation tasks
│   │   ├── research_tasks.py     # Research question generation
│   │   └── rag_tasks.py          # RAG corpus processing
│   ├── database/                 # Database layer
│   │   ├── models.py             # SQLAlchemy database models
│   │   └── default_prompts/      # Default LLM prompts
│   ├── pdf_processing/           # PDF processing and AI extraction
│   │   ├── ocr_processor.py      # OCR with rotation detection
│   │   ├── llm_genealogy_extractor.py # AI-powered data extraction
│   │   └── genealogy_model_benchmark.py # LLM model testing
│   ├── shared/                   # Common utilities
│   │   ├── gedcom_parser.py      # GEDCOM file parsing
│   │   ├── gedcom_writer.py      # GEDCOM file generation
│   │   ├── dutch_utils.py        # Dutch name/language utilities
│   │   └── logging_config.py     # Logging configuration
│   └── templates/                # Jinja2 templates
├── tests/                        # Comprehensive test suite (625 tests)
├── migrations/                   # Database migrations
└── requirements.txt             # Dependencies
```

## Development Environment

**Setup:**
```bash
source .venv/bin/activate         # MANDATORY - always activate first
export FLASK_APP=web_app
```

**Web Interface:**
```bash
flask run                        # Visit http://localhost:5000
```

**Docker Development:**
```bash
docker-compose up                # PostgreSQL + web app
# Visit http://localhost:5000
```

## Key Technical Details

- **Family-Focused Extraction**: LLM extracts family units with parent-child relationships, not just isolated individuals
- **Dutch Language Support**: Handles Dutch text, names, and genealogical conventions
- **Genealogical Symbols**: * (birth), ~ (baptism), † (death), x (marriage)
- **Generation Linking**: Tracks generation numbers and family group identifiers
- **LLM Models**: aya:35b-23 default model for structured extraction (configurable)
- **Hybrid Search**: Combines vector similarity, trigram matching, full-text search, and phonetic matching
- **Progress Tracking**: Real-time progress updates for long-running extractions

## Architecture Status (August 2025)

### ✅ **COMPLETED: Core Infrastructure**

**Service Layer (7 Services)**
- ✅ **Clean Architecture**: No global instances, proper dependency injection
- ✅ **Repository Pattern**: All services use repositories for data access
- ✅ **Base Classes**: `BaseRepository` and `ModelRepository<T>` for consistency
- ✅ **Error Handling**: Comprehensive exception handling and logging
- ✅ **Transaction Management**: Repositories use `flush()`, services manage transactions

**Repository Layer**
- ✅ **Inheritance Hierarchy**: `BaseRepository` → `GenealogyBaseRepository` → specialized repositories
- ✅ **Code Consolidation**: Eliminated duplicate place management and person creation logic
- ✅ **Type Safety**: Generic `ModelRepository<T>` for single-model operations
- ✅ **Caching**: Built-in caching for frequently accessed entities

**Blueprint Architecture**
- ✅ **Modular Design**: Each blueprint has focused, single responsibility
- ✅ **Standardized Error Handling**: Consistent error responses across all blueprints
- ✅ **Proper Registration**: All blueprints registered in Flask app factory

**Background Processing**
- ✅ **Celery Integration**: Robust task processing with progress tracking
- ✅ **File Management**: Download system for generated files (GEDCOM, research questions)
- ✅ **Error Recovery**: Automatic retries and comprehensive error handling

**Database Layer**
- ✅ **PostgreSQL + pgvector**: Full-text search, vector embeddings, and trigram matching
- ✅ **Comprehensive Models**: Person, Family, Place, Event, Marriage, Occupation entities
- ✅ **RAG Support**: TextCorpus, SourceText, Query models with genealogical context
- ✅ **Migration System**: Alembic migrations for schema evolution

**Testing Infrastructure**
- ✅ **625 Tests Passing**: 100% pass rate with comprehensive coverage
- ✅ **pytest-flask Integration**: Automatic Flask context management
- ✅ **Repository Testing**: Full test coverage for all repository patterns
- ✅ **Service Testing**: Mocked dependencies and error scenario testing

## Current Feature Status

### ✅ **FULLY IMPLEMENTED**

1. **OCR Processing** - PDF processing with database storage and progress tracking
2. **LLM Extraction** - Family-focused genealogy extraction with chunk processing  
3. **GEDCOM Generation** - Export to standard genealogy format with download
4. **Research Questions** - AI-generated research directions with file download
5. **Entity Management** - Person/Family/Place browsing and relationship tracking
6. **Prompt Management** - Database-stored prompts with web editing interface
7. **RAG Backend** - Text chunking, embeddings, hybrid search with genealogical context
8. **Job Management Backend** - Task submission, progress tracking, file downloads

### 🟡 **PARTIALLY IMPLEMENTED**

1. **Job Status Polling** 
   - ✅ Backend API exists and works
   - ❌ Frontend polling/refresh UI missing
   - **Impact**: Users can't see real-time job progress

2. **RAG Query Interface**
   - ✅ Complete backend with conversation awareness
   - ✅ Corpus management interface
   - ❌ Query input form and results display missing
   - **Impact**: Can manage corpora but can't query them

3. **Dashboard Consolidation**
   - ✅ All tool functionality works
   - ❌ Navigation between tools could be clearer
   - **Impact**: Users might get confused about workflow

## Configuration

**Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/family_wiki

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Ollama (LLM Server)
OLLAMA_HOST=192.168.1.234           # or localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=aya:35b-23

# Flask
SECRET_KEY=your-secret-key
```

**Database Models:**
- **Core Entities**: `Person`, `Family`, `Place`, `Event`, `Marriage`, `Occupation`
- **RAG Components**: `TextCorpus`, `SourceText`, `Query`
- **Management**: `ExtractionPrompt`, `Source`, `JobFile`

## Development Workflow

**CRITICAL REQUIREMENTS:**

**Virtual Environment (MANDATORY):**
- **ALWAYS** activate: `source .venv/bin/activate` before ANY Python commands
- **NEVER** run pytest/ruff/flask commands without virtualenv
- **CRITICAL**: Remember to activate after conversation compaction

**Quality Gates (MANDATORY):**
- **Tests**: `pytest` (must pass all 625 tests)
- **Linting**: `ruff check .` (must be clean)
- **Coverage**: Maintain >90% test coverage

**Development Principles:**
- **Simplest Approach**: Choose the simplest solution that solves the problem
- **Value Verification**: Confirm tasks are worth doing before starting
- **Repository Pattern**: Services use repositories, no direct database access
- **No Global Instances**: Always instantiate services/repositories when needed

**Testing:**
```bash
# Full test suite
pytest                              # All 625 tests

# Specific areas
pytest tests/test_services.py       # Service layer
pytest tests/test_repositories.py   # Repository layer  
pytest tests/test_blueprint*.py     # Blueprint integration

# Coverage report
pytest --cov=web_app --cov-report=html --cov-fail-under=90
```

**Architecture Guidelines:**
- **Services**: Business logic, use repositories for data access
- **Repositories**: Data access, use `flush()` not `commit()`
- **Blueprints**: Web routes, use services for business logic
- **Tasks**: Background processing, manage own transactions

## Quick Implementation Tasks

### **High-Impact Frontend Tasks (1-2 days each)**

1. **Job Status Polling UI** - Add JavaScript polling to job management pages
2. **RAG Query Interface** - Create query form and results display
3. **Navigation Improvements** - Clearer workflow paths between tools

### **Enhancement Tasks (0.5-1 day each)**

4. **Research Questions Display** - Better formatting and export options
5. **Error Message Improvements** - More user-friendly error displays  
6. **Mobile Responsiveness** - Better mobile experience for forms

## Project Health Summary

**✅ STRENGTHS:**
- **Solid Architecture**: Clean service/repository patterns, no technical debt
- **Comprehensive Testing**: 625 tests with 100% pass rate
- **Complete Backend**: All core business logic implemented and working
- **Scalable Design**: Modular blueprints, base classes, proper dependency injection

**🎯 FOCUS AREAS:**
- **Frontend Polish**: The backend is complete, focus on user experience
- **Real-time Feedback**: Job status polling is the highest-impact missing piece
- **Query Interface**: RAG system needs frontend to be usable

**💡 KEY INSIGHT:** This project has excellent foundational architecture. The "missing" features are primarily frontend/UI elements, not broken backend functionality. The development effort should focus on user interface completion rather than architectural changes.

**Current State**: Ready for feature completion and production deployment. Core functionality is solid and well-tested.