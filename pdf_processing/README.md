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
AI-powered genealogy extraction using local LLMs (Ollama) with **family-focused extraction**.

**Features:**
- **Family-centric extraction**: Groups people into family units with parent-child relationships
- **Generation linking**: Tracks generation numbers and family group identifiers (e.g., "III.2")
- **Dutch genealogy patterns**: Specifically looks for "Kinderen van" (children of) phrases
- Understands Dutch genealogical conventions (* birth, ~ baptism, † death, x marriage)
- **Relationship preservation**: Maintains family connections and cross-references
- Context-aware extraction with confidence scoring for relationships
- Uses qwen2.5:7b model by default
- Intelligent text chunking for optimal processing

**Output Format:**
The extractor now produces structured family data instead of isolated individuals:
- `families[]`: Family groups with parents and children
- `isolated_individuals[]`: People who couldn't be linked to families
- Each family includes generation numbers and family identifiers
- Parent-child relationships are explicitly preserved

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