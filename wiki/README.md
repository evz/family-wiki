# Wiki Generator

This directory will contain tools for generating a MediaWiki-based family wiki with person pages, places, and events.

## Planned Components

### Wiki Page Generation
- **Person pages**: Individual biography pages with genealogical data
- **Place pages**: Geographic locations with family connections
- **Event pages**: Family events, weddings, reunions, etc.

### MediaWiki Integration
- **Bulk import API**: Automated page creation
- **Template system**: Consistent formatting for person/place pages
- **Category management**: Automatic categorization by generation, location

### Data Sources
- Uses `../shared_genealogy/` utilities for data models
- Imports from GEDCOM files
- Processes LLM extraction results

## Status

🚧 **In Development** - Awaiting completion of PDF processing pipeline

The wiki generator will be implemented after the core genealogy extraction is complete. It will leverage the shared genealogy utilities and Person/Place/Event models already established.

## Future Usage

```bash
cd wiki
python wiki_generator.py --input ../llm_genealogy_results.json
python place_generator.py --gedcom ../family_tree.ged
python event_generator.py --source ../pdf_processing/extracted_text/
```