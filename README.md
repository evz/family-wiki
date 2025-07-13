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

**Unified Flask Application:**
```
app.py                         # Main Flask app with CLI commands
├── web_app/services/          # Shared business logic
├── web_app/blueprints/        # Web routes and API endpoints  
├── web_app/static/           # CSS and JavaScript
├── templates/                # Jinja2 templates
├── pdf_processing/           # PDF and OCR tools
├── shared_genealogy/         # Common utilities
└── tests/                    # Test suite
```

**Key Benefits:**
- **Shared Services**: Both CLI and web use the same business logic
- **No Subprocess Calls**: Web interface directly uses service classes
- **Progress Tracking**: Real-time updates for long-running tasks
- **Professional UI**: Modern design with progress bars and summaries

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

**Family-Focused Extraction:**
- Groups people into family units with parent-child relationships
- Tracks generation numbers and family identifiers
- Recognizes Dutch genealogy patterns like "Kinderen van" (children of)

**Dutch Language Support:**
- Handles Dutch text, names, and genealogical conventions
- Recognizes symbols: * (birth), ~ (baptism), † (death), x (marriage)
- Processes Dutch name particles (van, de, etc.)

**Progress Tracking:**
- Real-time progress updates for long-running extractions
- Task management with status monitoring
- Visual progress bars and summaries

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
# Run tests
pytest

# Start development server
flask run --debug

# Check project status
flask status
```

## Documentation

- See `CLAUDE.md` for detailed development context
- Each service module contains inline documentation
- Web interface includes built-in CLI help