# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an advanced AI-powered genealogy digitization and wiki generation system. The project processes a Dutch family history book (101 PDF pages) using OCR and LLM technology, with the ultimate goal of creating a comprehensive MediaWiki instance for family research.

**Complete Vision:**
- **Input Sources**: Dutch family book PDFs + existing GEDCOM files from other family branches
- **Processing Pipeline**: OCR → LLM extraction → GEDCOM generation → MediaWiki bulk import
- **Final Output**: MediaWiki instance with structured pages for:
  - Individual people and their biographical information
  - Family events (births, baptisms, marriages, deaths)
  - Places and residency periods with date ranges
  - Historical family connections and relationships

**Integration Strategy:**
- GEDCOM serves as the universal interchange format for combining multiple family data sources
- MediaWiki provides the research platform with cross-referenced family information
- Bulk page creation tools enable systematic population of the family wiki
- Existing GEDCOM files from other family branches can be imported alongside newly extracted book data

## Project Structure

```
family-wiki/
├── pdf_processing/                 # OCR and text processing tools
│   ├── pdfs/                       # 101 PDF pages of Dutch family book
│   ├── extracted_text/             # OCR results (created during processing)
│   ├── ocr_processor.py           # OCR with rotation detection
│   ├── llm_genealogy_extractor.py # AI-powered data extraction
│   └── genealogy_model_benchmark.py # LLM model testing
├── shared_genealogy/              # Shared utilities and data models
│   ├── models.py                  # Data models for persons, families, events
│   ├── gedcom_parser.py           # GEDCOM file parsing
│   ├── gedcom_writer.py           # GEDCOM file generation
│   ├── dutch_utils.py             # Dutch name/language utilities
│   └── logging_config.py          # Common logging configuration
├── tests/                         # Test suite
│   ├── conftest.py                # Pytest configuration and fixtures
│   ├── test_cli.py                # CLI interface tests
│   ├── test_logging_config.py     # Logging tests
│   └── test_models.py             # Data model tests
├── templates/                     # Flask web interface templates
├── logs/                          # Application logs (created at runtime)
├── family_wiki_cli.py             # Unified CLI interface
├── web_interface.py               # Flask web interface
├── gedcom_generator.py            # GEDCOM file creation
├── research_question_generator.py # Intelligent research questions
├── requirements.txt               # Python dependencies
├── pytest.ini                    # Pytest configuration
└── wiki/                          # Wiki generation tools (future development)
```

## Workflow

**Modern Approach (Recommended):**
1. **OCR Processing**: `python family_wiki_cli.py ocr`
   - Extracts text from all 101 PDFs with rotation correction
   - Creates consolidated text file

2. **Model Selection**: `python family_wiki_cli.py benchmark`
   - Tests multiple LLM models for genealogy extraction
   - Recommends optimal model for your system

3. **LLM Extraction**: `python family_wiki_cli.py extract`
   - Intelligent extraction of family data from Dutch text
   - Produces structured genealogical data

4. **GEDCOM Generation**: `python family_wiki_cli.py gedcom`
   - Creates standard genealogy files from LLM results

5. **Research Questions**: `python family_wiki_cli.py research`
   - Generates intelligent research directions

6. **Complete Pipeline**: `python family_wiki_cli.py pipeline`
   - Runs all steps above in sequence with proper error handling

**Alternative: Web Interface**
- Run `python web_interface.py` and access http://localhost:5000
- Browser-based interface for all tools with real-time progress
- View logs and results through web interface

## Key Technical Notes

- **Dutch Language**: All processing handles Dutch text, names, and conventions
- **Genealogical Symbols**: * (birth), ~ (baptism), † (death), x (marriage)
- **LLM Models**: Qwen2.5:7b recommended for structured extraction
- **Tussenvoegsel**: Handle Dutch name particles (van, de, der, etc.)
- **OCR Resilience**: LLM approach adapts to OCR errors and formatting variations

## Development Commands

**New Unified CLI Interface:**
```bash
# Setup
./setup.sh && source .venv/bin/activate

# Using the new CLI interface (recommended)
python family_wiki_cli.py --help           # Show all available commands
python family_wiki_cli.py ocr              # Run OCR processing
python family_wiki_cli.py benchmark        # Test LLM models
python family_wiki_cli.py extract          # Run AI extraction
python family_wiki_cli.py gedcom           # Generate GEDCOM files
python family_wiki_cli.py research         # Generate research questions
python family_wiki_cli.py pipeline         # Run complete pipeline
python family_wiki_cli.py --verbose pipeline # Run with detailed logging

# Web Interface
python web_interface.py                    # Start Flask web interface on http://localhost:5000

# Testing
pytest                                      # Run all tests
pytest tests/test_cli.py                   # Run specific test file
pytest -v                                  # Verbose test output
```

**Legacy Commands (still work):**
```bash
# Activate virtual environment first
source .venv/bin/activate

# Direct module execution (legacy)
cd pdf_processing
python ocr_processor.py             # Extract text from PDFs  
python genealogy_model_benchmark.py # Find best LLM model
python llm_genealogy_extractor.py   # AI extraction
cd ..
python gedcom_generator.py          # Create genealogy file
python research_question_generator.py # Generate research questions
```

## Processing Strategy

The LLM-based approach is robust and self-contained:
- No dependency on complex format parsing
- Handles Dutch genealogical conventions naturally
- Adapts to OCR variations and formatting inconsistencies
- Produces structured family data with confidence scoring

## Project Organization Notes

**Recent Reorganization (July 2025)**: 
- **Structure**: Moved `pdfs/` and `extracted_text/` folders into `pdf_processing/` for better logical grouping
- **CLI Interface**: Added unified `family_wiki_cli.py` using Click for consistent command-line access
- **Web Interface**: Created Flask-based `web_interface.py` for browser access to all tools
- **Testing**: Implemented pytest test suite with fixtures and common test patterns
- **Logging**: Standardized logging across all modules with configurable levels and file output
- **Dependencies**: Pinned all package versions for stability and reproducibility
- **Cleanup**: Removed unused files and consolidated all tools under common interfaces
- Project now has professional tooling with CLI, web interface, testing, and logging