# Family Wiki Tools

A unified Flask application for AI-powered genealogy digitization. Process Dutch family history books using OCR and Large Language Models to extract structured family data.

## Features

- **🔍 OCR Processing**: Extract text from PDF scans with rotation detection
- **🤖 Family-Focused AI Extraction**: Group people into family units with parent-child relationships  
- **📜 GEDCOM Generation**: Create standard genealogy files
- **🔬 Research Questions**: Generate intelligent research directions
- **⚡ Model Benchmarking**: Test multiple LLM models for optimal performance
- **🌐 Web Interface**: Real-time progress tracking and visual summaries
- **⌨️ CLI Commands**: Professional command-line interface with `flask <command>`

## Quick Start

```bash
# Setup
./setup.sh && source .venv/bin/activate
export FLASK_APP=app.py

# Web interface
flask run
# Visit http://localhost:5000

# CLI tools
flask ocr              # Extract text from PDFs
flask extract          # AI-powered family extraction
flask gedcom           # Generate GEDCOM files
flask research         # Generate research questions
flask pipeline         # Run complete workflow
```

## Architecture

**Database-Driven Flask Application:**
```
app.py                         # Main Flask app with CLI commands
├── web_app/
│   ├── services/              # Business logic services
│   ├── blueprints/            # Web routes and API endpoints  
│   ├── repositories/          # Database operations layer
│   ├── shared/                # Common utilities and parsers
│   ├── database/              # SQLAlchemy models and config
│   └── static/                # CSS and JavaScript
├── templates/                 # Jinja2 templates
├── pdf_processing/            # PDF and OCR tools
└── tests/                     # Comprehensive test suite (91% coverage)
```

**Key Benefits:**
- **Database Integration**: PostgreSQL with pgvector for semantic search
- **Repository Pattern**: Clean separation of database operations
- **API Blueprints**: Organized REST endpoints for all functionality
- **Dutch Language Support**: Specialized parser for Dutch genealogy patterns
- **RAG System**: Retrieval-augmented generation for intelligent queries
- **91% Test Coverage**: Comprehensive testing with quality gates

## Usage

**Web Interface** (Recommended for interactive use):
```bash
flask run
# Visit http://localhost:5000
```
- Real-time progress tracking
- Visual summaries and results
- Easy access to all tools

**CLI Commands** (Perfect for automation):
```bash
flask ocr --verbose           # OCR with detailed output
flask extract                 # AI-powered extraction
flask gedcom                  # Generate GEDCOM files
flask research                # Generate research questions
flask benchmark               # Test LLM models
flask pipeline                # Complete workflow
flask status                  # System status check
```

## Key Features

**Database-Driven Architecture:**
- PostgreSQL with pgvector for semantic similarity search
- Repository pattern for clean database operations
- Comprehensive entity relationships (Person, Family, Place, Event)
- RAG (Retrieval-Augmented Generation) for intelligent queries

**Family-Focused Extraction:**
- Groups people into family units with parent-child relationships
- Tracks generation numbers and family identifiers
- Recognizes Dutch genealogy patterns like "Kinderen van" (children of)

**Dutch Language Support:**
- Specialized Dutch genealogy parser with 94% test coverage
- Handles Dutch text, names, and genealogical conventions
- Recognizes symbols: * (birth), ~ (baptism), † (death), x (marriage)
- Processes Dutch name particles (van, de, etc.) with proper tussenvoegsel handling

**Quality Assurance:**
- 91% test coverage with comprehensive error handling
- Repository pattern for database operations
- API blueprint organization for clean endpoints
- Mandatory linting and testing quality gates

## Requirements

- Python 3.8+
- Flask framework
- Tesseract OCR (for PDF processing)
- Ollama (for LLM models)
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
ollama pull qwen2.5:7b

# Set Flask app
export FLASK_APP=app.py
```

## Development

```bash
# Setup virtual environment (MANDATORY)
source .venv/bin/activate
export FLASK_APP=app.py

# Run tests (91% coverage)
pytest
pytest --cov=web_app --cov-report=html --cov-report=term-missing

# Run linting
ruff check .
ruff check . --fix

# Start development server
flask run --debug

# Check project status
flask status

# Database operations
flask db-clear              # Clear database (development)
flask db-stats              # Database statistics
```

**Quality Gates:**
- All code must pass `ruff check .` (linting)
- All tests must pass with >90% coverage
- Repository pattern enforced for database operations
- API blueprint organization for clean endpoints

## Documentation

- See `CLAUDE.md` for detailed development context
- Each service module contains inline documentation
- Web interface includes built-in CLI help