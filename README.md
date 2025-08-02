# Family Wiki Tools

A unified Flask application for AI-powered genealogy digitization. Process Dutch family history books using OCR and Large Language Models to extract structured family data.

## Core Features

- **🔍 OCR Processing**: Extract text from PDF scans with rotation detection
- **🤖 Family-Focused AI Extraction**: Group people into family units with parent-child relationships  
- **📜 GEDCOM Generation**: Create standard genealogy files from extracted data
- **🔬 Research Questions**: Generate intelligent research directions from family data
- **⚡ Model Benchmarking**: Test multiple LLM models for optimal extraction performance
- **🌐 Web Interface**: Browser-based access to all tools with progress tracking
- **🔍 RAG Queries**: Ask questions about source texts using semantic search

## Quick Start

```bash
# Setup
./setup.sh && source .venv/bin/activate
export FLASK_APP=app.py

# Start web application
flask run
# Visit http://localhost:5000

# Docker Development (Alternative)
make dev               # Start with mDNS resolution + host networking
# OR
docker-compose up      # Start PostgreSQL + web app
```

## Architecture

**Database-Driven Flask Application:**
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
│   │   ├── entities.py           # Entity browsing interface
│   │   ├── rag.py                # RAG query interface
│   │   ├── ocr.py                # OCR processing operations
│   │   ├── extraction.py         # LLM genealogy data extraction
│   │   ├── gedcom.py             # GEDCOM file generation
│   │   ├── research.py           # Research questions generation + viewing
│   │   └── jobs.py               # Job management (status, cancellation, downloads)
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
│   │   ├── rag_tasks.py          # RAG processing tasks
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
│   └── static/                   # Web interface assets
├── templates/                    # Jinja2 templates
├── tests/                        # Comprehensive test suite
└── requirements.txt             # Dependencies
```

**Key Benefits:**
- **Modular Blueprints**: Each feature has its own focused blueprint with standardized error handling
- **Service Layer**: Shared business logic used by web interface and background tasks
- **Background Tasks**: Celery tasks for long-running operations with progress tracking
- **Repository Pattern**: Clean separation of database operations
- **PostgreSQL + pgvector**: Full text search and semantic similarity capabilities
- **85%+ Test Coverage**: Comprehensive testing with quality gates

## Available Features

**Web Interface** (Primary method of interaction):
```bash
flask run
# Visit http://localhost:5000
```

**Available Features:**
- **Entity Browser** (`/entities/`) - View extracted Person/Family/Place entities
- **RAG Queries** (`/rag/`) - Ask questions about source texts using semantic search
- **OCR Processing** (`/ocr/`) - Extract text from PDF scans
- **LLM Extraction** (`/extraction/`) - AI-powered genealogy data extraction
- **GEDCOM Generation** (`/gedcom/`) - Export to standard genealogy format
- **Research Questions** (`/research/`) - Generate intelligent research directions
- **Job Management** (`/jobs/`) - Monitor background task progress

## Current Status

**✅ Fully Implemented:**
- **Core Business Logic**: Complete service layer with 85%+ test coverage
- **Database Architecture**: PostgreSQL with pgvector, full RAG capabilities
- **Background Processing**: Celery tasks for OCR, extraction, GEDCOM, research questions  
- **Web Interface**: Modular Flask blueprints with comprehensive error handling
- **Entity Management**: Person/Family/Place browsing and management
- **Dutch Language Support**: Specialized genealogy parsing with tussenvoegsel handling
- **Test Infrastructure**: 345+ tests passing (100% pass rate) with pytest-flask integration

**🔄 Partially Complete:**
- **RAG Query Interface**: Backend complete, frontend forms missing
- **Job Status Polling**: Task submission works but limited real-time feedback
- **Research Questions**: Core functionality complete but method name mismatch prevents execution

**Key Technical Features:**
- **Family-Focused Extraction**: Groups people into family units with parent-child relationships
- **Dutch Genealogy Patterns**: Recognizes "Kinderen van" (children of) and genealogical symbols (* birth, ~ baptism, † death, x marriage)
- **Repository Pattern**: Clean separation of database operations with comprehensive error handling  
- **Standardized Error Handling**: Consistent error responses across all blueprints
- **Progress Tracking**: Real-time updates for long-running extraction operations

## Requirements

- Python 3.8+
- PostgreSQL with pgvector extension
- Tesseract OCR (for PDF processing)
- Ollama (for LLM models - default: aya:35b-23)
- Celery + Redis/RabbitMQ (for background tasks)
- 8GB+ RAM recommended for optimal LLM performance

## Installation

```bash
# Clone and setup
git clone <repository>
cd family-wiki
./setup.sh
source .venv/bin/activate

# Install Ollama for LLM processing
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull aya:35b-23

# Setup PostgreSQL with pgvector
# (Instructions vary by OS - see Docker option below for easier setup)

# Set Flask app
export FLASK_APP=app.py

# Docker option (recommended for development)
docker-compose up  # Starts PostgreSQL + pgvector + web app
```

## Development

```bash
# Setup virtual environment (MANDATORY)
source .venv/bin/activate
export FLASK_APP=app.py

# Run tests (85%+ coverage requirement)
pytest
pytest --cov=web_app --cov-report=html --cov-report=term-missing --cov-fail-under=85

# Run linting
ruff check .
ruff check . --fix

# Start development server
flask run --debug
```

**Quality Gates:**
- All code must pass `ruff check .` (linting)
- All tests must pass with >85% coverage
- Repository pattern enforced for database operations
- Modular blueprint organization with standardized error handling

## Documentation

- See `CLAUDE.md` for detailed development context
- Each service module contains inline documentation
- Web interface includes built-in CLI help