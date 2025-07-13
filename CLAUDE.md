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
├── web_app/                       # Web application package
│   ├── services/                  # Shared business logic
│   │   ├── extraction_service.py  # LLM extraction with progress tracking
│   │   ├── ocr_service.py         # OCR processing service
│   │   ├── gedcom_service.py      # GEDCOM generation service
│   │   ├── research_service.py    # Research questions service
│   │   └── benchmark_service.py   # Model benchmarking service
│   ├── blueprints/               # Flask blueprints
│   │   ├── main.py               # Main web routes
│   │   └── extraction.py         # Extraction API endpoints
│   ├── static/                   # Static web assets
│   │   ├── css/main.css          # Professional styling
│   │   └── js/                   # JavaScript modules
│   │       ├── main.js           # Core utilities
│   │       └── extraction.js     # Progress tracking for extraction
│   └── commands.py               # Flask CLI command definitions
├── pdf_processing/               # Original processing tools
│   ├── pdfs/                     # PDF files to process
│   ├── extracted_text/           # OCR output files
│   └── *.py                      # Processing modules
├── shared_genealogy/             # Common utilities
│   ├── models.py                 # Data models
│   ├── gedcom_*.py              # GEDCOM utilities
│   ├── dutch_utils.py           # Dutch language support
│   └── logging_config.py        # Logging configuration
├── templates/                    # Jinja2 templates
├── tests/                        # Test suite
│   ├── test_services.py         # Service layer tests
│   ├── test_flask_app.py        # Flask app and CLI tests
│   └── test_*.py                # Additional tests
├── gedcom_generator.py          # GEDCOM generation
├── research_question_generator.py # Research questions
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
- **LLM Models**: Qwen2.5:7b recommended for structured extraction
- **Progress Tracking**: Real-time progress updates for long-running extractions

## Development

**Setup:**
```bash
./setup.sh && source .venv/bin/activate
export FLASK_APP=app.py
```

**Testing:**
```bash
pytest                              # Run all tests
pytest tests/test_services.py       # Test service layer
pytest tests/test_flask_app.py      # Test Flask app and CLI
pytest -v                          # Verbose output
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
```