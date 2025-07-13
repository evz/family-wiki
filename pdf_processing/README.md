# PDF Processing Tools

This directory contains tools for extracting and processing genealogical data from PDF scans of family history books.

## Scripts

### `ocr_processor.py`
OCR processing with rotation detection for upside-down pages.

**Features:**
- Dutch + English language support
- Automatic rotation detection and correction
- 2x image scaling for better OCR accuracy
- Processes all PDFs in batch

**Usage:**
```bash
cd pdf_processing
python ocr_processor.py
```

### `llm_genealogy_extractor.py`
AI-powered genealogy extraction using local LLMs (Ollama).

**Features:**
- Understands Dutch genealogical conventions (* birth, ~ baptism, † death, x marriage)
- Context-aware extraction with confidence scoring
- Uses qwen2.5:7b model by default
- Intelligent text chunking for optimal processing

**Usage:**
```bash
cd pdf_processing
python llm_genealogy_extractor.py
```

### `genealogy_model_benchmark.py`
Benchmark different LLM models for genealogy extraction performance.

**Usage:**
```bash
cd pdf_processing
python genealogy_model_benchmark.py
```

## Dependencies

These scripts use the shared genealogy utilities from `../shared_genealogy/` for:
- Dutch name parsing (van, de, etc.)
- Date format conversion
- GEDCOM data structures

## Input/Output

- **Input**: `pdfs/` (PDF scans)
- **OCR Output**: `extracted_text/`
- **LLM Results**: `../llm_genealogy_results.json`