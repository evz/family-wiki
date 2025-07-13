# Family Wiki - Digital Genealogy Project

This project digitizes and analyzes a Dutch family history book using OCR and AI-powered text extraction to create structured genealogical data and a family wiki.

## Project Overview

**Goal**: Transform a physical family book (101 scanned PDF pages) into structured digital genealogy data, including:
- Clean text extraction from PDF scans
- Family tree structure identification  
- Biographical information extraction
- GEDCOM file generation for genealogy software
- MediaWiki-based family website generation
- Research question generation for further investigation

**Challenge**: The source material is a Dutch family history book with:
- Mixed Dutch and English text
- Some pages oriented upside-down
- Complex genealogical notation (*, ~, †, x symbols)
- Hierarchical family structure across multiple generations
- Handwritten annotations and varying print quality

## Project Structure

```
family-wiki/
├── pdf_processing/          # PDF and text extraction tools
│   ├── pdfs/                # Original scanned PDF pages (001.pdf - 101.pdf)
│   ├── extracted_text/      # OCR results (created during processing)
│   │   ├── 001.txt - 101.txt # Individual page extractions
│   │   └── consolidated_text.txt # Combined text from all pages
│   ├── ocr_processor.py     # OCR with rotation detection
│   ├── llm_genealogy_extractor.py # AI-powered family data extraction
│   ├── genealogy_model_benchmark.py # LLM model comparison
│   └── README.md           # PDF processing documentation
├── wiki/                   # MediaWiki family site generator
│   └── README.md           # Wiki generation documentation (planned)
├── shared_genealogy/       # Shared utilities and data models
│   ├── models.py           # Person, Family, Place, Event classes
│   ├── dutch_utils.py      # Dutch name/date/place parsing
│   ├── gedcom_parser.py    # GEDCOM file reading
│   ├── gedcom_writer.py    # GEDCOM file writing
│   └── __init__.py         # Module exports
├── gedcom_generator.py     # GEDCOM file creation (uses shared utilities)
├── research_question_generator.py # Research gap analysis
├── setup.sh                # Environment setup script
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── CLAUDE.md              # Development context for Claude Code
```

## Workflow

### Phase 1: PDF Text Extraction ✅
**Script**: `pdf_processing/ocr_processor.py`

Extract clean text from all 101 PDF pages:
- Handles upside-down page detection and rotation
- Uses Tesseract OCR with Dutch + English language support
- 2x image scaling for improved OCR accuracy
- Consolidates all text into a single file

**Usage**:
```bash
./setup.sh  # Install dependencies
source venv/bin/activate
cd pdf_processing
python ocr_processor.py
```

**Output**: `pdf_processing/extracted_text/consolidated_text.txt` - Raw OCR text from all pages

### Phase 2: AI-Powered Genealogy Extraction 🚀
**Script**: `pdf_processing/llm_genealogy_extractor.py`

Use Large Language Models to intelligently extract family data from Dutch genealogical text:

**Why LLM Approach**:
- Understands context and family relationships
- Handles Dutch language and genealogical conventions naturally
- Recognizes symbols: * (birth), ~ (baptism), † (death), x (marriage)
- Adapts to OCR errors and text variations
- Much more robust than regex pattern matching

**Model Selection**:
```bash
# Find optimal model for your system
cd pdf_processing
python genealogy_model_benchmark.py

# Run extraction with best model
python llm_genealogy_extractor.py
```

**Recommended Models**:
- `qwen2.5:7b` - Best for structured extraction
- `qwen2.5:3b` - Efficient for lower-end systems
- `llama3.1:8b` - Reliable general purpose

**Output**: `llm_genealogy_results.json` - Structured family data

### Phase 3: GEDCOM Generation 📋
**Script**: `gedcom_generator.py`

Convert extracted family data into standard genealogy format:
```bash
python gedcom_generator.py
```

**Compatible with**: Gramps, Family Tree Maker, Ancestry.com, MyHeritage

### Phase 4: Wiki Generation 🌐
**Location**: `wiki/`

Generate MediaWiki-based family website:
```bash
cd wiki
python wiki_generator.py
```

**Features**: Person pages, place pages, family events, automated categorization

### Phase 5: Research Question Generation 🔍
**Script**: `research_question_generator.py`

Generate intelligent research questions:
```bash
python research_question_generator.py
```

**Analyzes**:
- Missing vital records and biographical gaps
- Geographic migration patterns  
- Historical context and events
- Occupational and social patterns
- Naming conventions and variations

## Technical Details

### OCR Configuration
- **Languages**: Dutch (nld) + English (eng)
- **Mode**: PSM 6 (uniform text block)
- **Preprocessing**: Grayscale conversion, contrast enhancement
- **Rotation**: Automatic detection and correction

### AI Model Requirements
- **Local LLM**: Ollama with genealogy-optimized models
- **Memory**: 8GB+ RAM recommended for qwen2.5:7b
- **Processing**: CPU-based inference (GPU optional)

### Genealogical Symbol Recognition
The AI models are trained to understand Dutch genealogy conventions:
- `*` = geboren (born)
- `~` = gedoopt (baptized)  
- `†` or `+` = overleden (died)
- `x` = getrouwd (married)
- Letter sequences (a., b., c.) = siblings in birth order
- Roman numerals (I, II, III) = generation markers

### Data Quality
The LLM approach provides:
- **Confidence scores** for each extraction
- **Multi-pass validation** across different models
- **Context awareness** for relationship understanding
- **Error resilience** against OCR mistakes

### Shared Genealogy Utilities
The project includes reusable components in `shared_genealogy/`:
- **Data Models**: Person, Family, Place, Event classes with Dutch genealogy conventions
- **Name Parsing**: Handles Dutch particles (van, de, etc.) and naming conventions
- **Date Processing**: Converts Dutch date formats to standardized GEDCOM format
- **GEDCOM Support**: Full read/write capability for genealogy software compatibility
- **Place Processing**: Geographic location parsing and standardization

## Getting Started

1. **Setup Environment**:
   ```bash
   ./setup.sh
   source venv/bin/activate
   ```

2. **Install Ollama** (for LLM processing):
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

3. **Run Model Benchmark** (recommended):
   ```bash
   cd pdf_processing
   python genealogy_model_benchmark.py
   ```

4. **Extract Family Data**:
   ```bash
   python llm_genealogy_extractor.py
   ```

5. **Generate GEDCOM**:
   ```bash
   python gedcom_generator.py
   ```

6. **Create Wiki**:
   ```bash
   cd wiki
   python wiki_generator.py
   ```

## Current Status

**🆕 Fresh Start**: Project cleaned and ready for full processing

- **Source Material**: ✅ 101 PDF pages loaded and ready
- **OCR Pipeline**: ✅ Configured for Dutch/English with rotation detection
- **AI Models**: ✅ Benchmarking and extraction scripts ready
- **Next Step**: 🚀 Process all 101 PDFs with OCR
- **Then**: ⚡ AI-powered genealogy extraction
- **Then**: 📋 GEDCOM generation and wiki creation
- **Finally**: 🔍 Research analysis and gap identification

## Next Steps

1. **OCR Processing**: Extract text from all 101 PDF pages
   ```bash
   source venv/bin/activate
   cd pdf_processing
   python ocr_processor.py
   ```

2. **Model Selection**: Benchmark LLMs for optimal genealogy extraction
   ```bash
   python genealogy_model_benchmark.py
   ```

3. **AI Extraction**: Run intelligent family data extraction
   ```bash
   python llm_genealogy_extractor.py
   ```

4. **GEDCOM Generation**: Create standard genealogy file
   ```bash
   python gedcom_generator.py
   ```

5. **Wiki**: Create MediaWiki-based family website
   ```bash
   cd wiki
   python wiki_generator.py
   ```

6. **Analysis**: Generate research questions and identify gaps

## Why This Approach Works

**Traditional genealogy digitization** relies on manual transcription or simple pattern matching, which is:
- Time-intensive for large documents
- Error-prone with OCR artifacts  
- Inflexible with varying formats
- Limited by rigid parsing rules

**Our AI-powered approach** leverages modern LLMs to:
- Understand genealogical context and relationships
- Handle multiple languages naturally
- Adapt to OCR errors and format variations
- Extract structured data with confidence scoring
- Scale to large document collections

This represents a significant advancement in automated genealogy processing, combining OCR technology with modern AI language understanding for accurate family history digitization and interactive wiki generation.