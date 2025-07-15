#!/usr/bin/env python3
"""
LLM-powered genealogy extractor using local models (Ollama) or OpenAI
"""

import json
import logging
import re
from pathlib import Path

import requests


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMGenealogyExtractor:
    def __init__(self, text_file: str = "extracted_text/consolidated_text.txt",
                 ollama_host: str = "192.168.1.234", ollama_port: int = 11434,
                 ollama_model: str = "aya:35b-23"):
        self.text_file = Path(text_file)
        self.results = []

        # Configuration
        self.ollama_host = ollama_host
        self.ollama_port = ollama_port
        self.ollama_model = ollama_model
        self.ollama_base_url = f"http://{ollama_host}:{ollama_port}"

        # Try to detect available LLM services
        self.check_ollama()
        self.check_openai()

    def check_ollama(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"Ollama available at {self.ollama_base_url} with {len(models)} models")
                return True
        except Exception:
            logger.info(f"Ollama not available at {self.ollama_base_url}")
        return False

    def check_openai(self) -> bool:
        """Check if OpenAI API key is available"""
        import os
        if os.getenv('OPENAI_API_KEY'):
            logger.info("OpenAI API key found")
            return True
        else:
            logger.info("OpenAI API key not found")
        return False

    def query_ollama(self, prompt: str, model: str = None) -> str | None:
        """Query Ollama local LLM"""
        if model is None:
            model = self.ollama_model

        try:
            response = requests.post(f"{self.ollama_base_url}/api/generate",
                                   json={
                                       "model": model,
                                       "prompt": prompt,
                                       "stream": False,
                                       "options": {
                                           "temperature": 0.1,  # Low temperature for factual extraction
                                           "top_p": 0.9
                                       }
                                   },
                                   timeout=120)

            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            logger.error(f"Ollama query failed at {self.ollama_base_url}: {e}")
        return None

    def create_genealogy_prompt(self, text_chunk: str) -> str:
        """Create a specialized prompt for genealogical data extraction with family linking"""
        return f"""You are an expert Dutch genealogist. Analyze this historical family record text and extract structured family information with proper relationships.

IMPORTANT CONTEXT:
- This is Dutch genealogical text from a family book organized by generations
- * means birth, ~ means baptism, + means death, x means marriage
- Letters like "a.", "b.", "c." indicate siblings in birth order
- Patterns like "1.1" or "III.2" indicate family groups
- Look for phrases like "Kinderen van" (children of) to identify families
- Dutch place names and dates in DD.MM.YYYY format are common
- Names often include "van/de" indicating place of origin

TEXT TO ANALYZE:
{text_chunk}

Extract family groups and relationships. Return ONLY valid JSON in this exact format:
{{
  "families": [
    {{
      "family_id": "unique identifier like 'III.2' or descriptive name",
      "parents": {{
        "father": {{
          "given_names": "first and middle names",
          "surname": "family name including van/de prefixes",
          "birth_date": "date if mentioned with *",
          "birth_place": "place if mentioned with *",
          "baptism_date": "date if mentioned with ~",
          "baptism_place": "place if mentioned with ~",
          "death_date": "date if mentioned with +",
          "death_place": "place if mentioned with +",
          "marriage_date": "date if mentioned with x",
          "marriage_place": "place if mentioned with x",
          "notes": "additional information",
          "confidence": 0.85
        }},
        "mother": {{
          "given_names": "first and middle names",
          "surname": "maiden name including van/de prefixes",
          "birth_date": "date if mentioned with *",
          "birth_place": "place if mentioned with *",
          "baptism_date": "date if mentioned with ~",
          "baptism_place": "place if mentioned with ~",
          "death_date": "date if mentioned with +",
          "death_place": "place if mentioned with +",
          "marriage_date": "date if mentioned with x",
          "marriage_place": "place if mentioned with x",
          "notes": "additional information",
          "confidence": 0.85
        }}
      }},
      "children": [
        {{
          "given_names": "first and middle names",
          "surname": "inherited family name",
          "birth_date": "date if mentioned with *",
          "birth_place": "place if mentioned with *",
          "baptism_date": "date if mentioned with ~",
          "baptism_place": "place if mentioned with ~",
          "death_date": "date if mentioned with +",
          "death_place": "place if mentioned with +",
          "marriage_date": "date if mentioned with x",
          "marriage_place": "place if mentioned with x",
          "spouse_name": "spouse name if mentioned",
          "sibling_order": "a, b, c etc. if present",
          "notes": "additional information including any children mentioned",
          "confidence": 0.85
        }}
      ],
      "generation_number": "1, 2, 3 etc. if mentioned",
      "family_notes": "any notes about the family as a whole"
    }}
  ],
  "isolated_individuals": [
    {{
      "given_names": "first and middle names",
      "surname": "family name including van/de prefixes",
      "birth_date": "date if mentioned with *",
      "birth_place": "place if mentioned with *",
      "baptism_date": "date if mentioned with ~",
      "baptism_place": "place if mentioned with ~",
      "death_date": "date if mentioned with +",
      "death_place": "place if mentioned with +",
      "marriage_date": "date if mentioned with x",
      "marriage_place": "place if mentioned with x",
      "spouse_name": "spouse name if mentioned",
      "relationship_context": "how this person relates to families mentioned",
      "notes": "additional information",
      "confidence": 0.85
    }}
  ]
}}

EXTRACTION RULES:
1. PRIORITIZE FAMILY GROUPS - Look for "Kinderen van [parent names]" patterns
2. LINK GENERATIONS - If text mentions "eerste/tweede generatie" note the generation number
3. CONNECT RELATIONSHIPS - When someone is mentioned as parent in one section and child in another, note this
4. PRESERVE CONTEXT - Include family group identifiers and generation markers
5. USE CONFIDENCE SCORING:
   - 0.95+ for explicit family statements like "Kinderen van Jan en Maria:"
   - 0.85+ for clear relationships inferred from context
   - 0.7+ for probable relationships based on names/dates/places
6. Leave fields empty ("") if information is not clearly stated
7. Include Dutch names and places exactly as written
8. If no clear families are found, return empty families array []

Focus on creating a family tree structure rather than isolated individuals.

JSON RESPONSE:"""

    def extract_from_chunk(self, text_chunk: str, custom_prompt: str = None) -> dict:
        """Extract genealogical data from a text chunk using LLM"""
        if custom_prompt:
            # Use custom prompt with text substitution
            prompt = custom_prompt.replace("{text_chunk}", text_chunk)
        else:
            prompt = self.create_genealogy_prompt(text_chunk)

        # Try Ollama first
        response = self.query_ollama(prompt)

        if not response:
            logger.warning("LLM extraction failed for chunk")
            return {"families": [], "isolated_individuals": []}

        try:
            # Try to parse JSON from response
            # Sometimes LLMs add extra text, so find the JSON part
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                # Ensure proper structure
                if isinstance(data, dict):
                    return {
                        "families": data.get("families", []),
                        "isolated_individuals": data.get("isolated_individuals", [])
                    }
                else:
                    logger.warning("Response is not a dictionary")
                    return {"families": [], "isolated_individuals": []}
            else:
                logger.warning("No JSON found in LLM response")
                return {"families": [], "isolated_individuals": []}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response was: {response[:500]}...")
            return {"families": [], "isolated_individuals": []}

    def split_text_intelligently(self, text: str) -> list[str]:
        """Split text into meaningful chunks for LLM processing"""
        # Remove file markers and clean up
        text = re.sub(r'=== PAGE \d+ ===', '', text)
        text = re.sub(r'### FILE: \d+\.txt ###', '', text)
        text = re.sub(r'={20,}', '', text)

        chunks = []

        # Split by generation headers first
        generation_splits = re.split(r'(EERSTE|TWEEDE|DERDE|VIERDE|VIJFDE|ZESDE)\s+GENERATIE', text, flags=re.IGNORECASE)

        current_generation = ""
        for _i, section in enumerate(generation_splits):
            section = section.strip()
            if not section:
                continue

            # Check if this is a generation header
            if re.match(r'(EERSTE|TWEEDE|DERDE|VIERDE|VIJFDE|ZESDE)', section, re.IGNORECASE):
                current_generation = section + " GENERATIE"
                continue

            # Split further by family groups or natural breaks
            family_splits = re.split(r'(\d+\.?\d*\.\s+Kinderen van [^:]+:)', section)

            for _j, subsection in enumerate(family_splits):
                subsection = subsection.strip()
                if len(subsection) > 100:  # Only process substantial chunks
                    chunk_text = f"{current_generation}\n\n{subsection}" if current_generation else subsection
                    chunks.append(chunk_text[:4000])  # Limit chunk size for LLM

        logger.info(f"Created {len(chunks)} text chunks for analysis")
        return chunks

    def process_all_text(self) -> None:
        """Process the entire family book text"""
        if not self.text_file.exists():
            logger.error(f"Text file not found: {self.text_file}")
            return

        with open(self.text_file, encoding='utf-8') as f:
            content = f.read()

        chunks = self.split_text_intelligently(content)

        all_families = []
        all_isolated_individuals = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")

            chunk_data = self.extract_from_chunk(chunk)

            # Add chunk metadata to families
            for family in chunk_data.get("families", []):
                family['chunk_id'] = i
                family['extraction_method'] = 'llm'
                # Add chunk metadata to family members
                if 'parents' in family:
                    if 'father' in family['parents'] and family['parents']['father']:
                        family['parents']['father']['chunk_id'] = i
                    if 'mother' in family['parents'] and family['parents']['mother']:
                        family['parents']['mother']['chunk_id'] = i
                for child in family.get('children', []):
                    child['chunk_id'] = i

            # Add chunk metadata to isolated individuals
            for person in chunk_data.get("isolated_individuals", []):
                person['chunk_id'] = i
                person['extraction_method'] = 'llm'

            all_families.extend(chunk_data.get("families", []))
            all_isolated_individuals.extend(chunk_data.get("isolated_individuals", []))

            # Small delay to be nice to the LLM
            import time
            time.sleep(1)

        self.results = {
            "families": all_families,
            "isolated_individuals": all_isolated_individuals
        }

        total_people = sum(len(f.get('children', [])) for f in all_families)
        total_people += sum(1 for f in all_families if f.get('parents', {}).get('father'))
        total_people += sum(1 for f in all_families if f.get('parents', {}).get('mother'))
        total_people += len(all_isolated_individuals)

        logger.info(f"Extraction complete: found {len(all_families)} families, {len(all_isolated_individuals)} isolated individuals, {total_people} total people")

    def save_results(self, output_file: str = "llm_genealogy_results.json") -> None:
        """Save LLM extraction results"""
        output_path = Path(output_file)

        # Calculate statistics
        families = self.results.get("families", [])
        isolated_individuals = self.results.get("isolated_individuals", [])

        total_people = sum(len(f.get('children', [])) for f in families)
        total_people += sum(1 for f in families if f.get('parents', {}).get('father'))
        total_people += sum(1 for f in families if f.get('parents', {}).get('mother'))
        total_people += len(isolated_individuals)

        data = {
            'metadata': {
                'total_families': len(families),
                'total_isolated_individuals': len(isolated_individuals),
                'total_people': total_people,
                'extraction_method': 'llm_powered_family_focused',
                'model_used': 'ollama_llama3.1'
            },
            'families': families,
            'isolated_individuals': isolated_individuals
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_path}")

    def get_extraction_summary(self) -> dict:
        """Get extraction summary as structured data"""
        families = self.results.get("families", [])
        isolated_individuals = self.results.get("isolated_individuals", [])
        total_people = self._calculate_total_people(self.results)

        summary = {
            'total_families': len(families),
            'total_isolated_individuals': len(isolated_individuals),
            'total_people': total_people
        }

        if families:
            total_children = sum(len(f.get('children', [])) for f in families)
            families_with_parents = sum(1 for f in families
                                      if f.get('parents', {}).get('father') or f.get('parents', {}).get('mother'))
            families_with_generation = sum(1 for f in families if f.get('generation_number'))

            summary.update({
                'average_children_per_family': total_children / len(families) if families else 0,
                'families_with_parents': families_with_parents,
                'families_with_generation': families_with_generation,
                'sample_families': self._get_sample_families(families[:3])
            })

        if isolated_individuals:
            summary['sample_isolated'] = self._get_sample_isolated(isolated_individuals[:3])

        return summary

    def _get_sample_families(self, families: list) -> list:
        """Get sample family data for summary"""
        samples = []
        for i, family in enumerate(families):
            father_name = ""
            mother_name = ""
            if family.get('parents'):
                if family['parents'].get('father'):
                    father = family['parents']['father']
                    father_name = f"{father.get('given_names', '')} {father.get('surname', '')}".strip()
                if family['parents'].get('mother'):
                    mother = family['parents']['mother']
                    mother_name = f"{mother.get('given_names', '')} {mother.get('surname', '')}".strip()

            samples.append({
                'family_id': family.get('family_id', f'Family {i+1}'),
                'parents': f"{father_name} & {mother_name}" if father_name and mother_name else father_name or mother_name or "Unknown",
                'children_count': len(family.get('children', [])),
                'generation': family.get('generation_number', 'Unknown')
            })
        return samples

    def _get_sample_isolated(self, individuals: list) -> list:
        """Get sample isolated individual data for summary"""
        samples = []
        for person in individuals:
            name = f"{person.get('given_names', '')} {person.get('surname', '')}".strip()
            samples.append({
                'name': name,
                'birth_date': person.get('birth_date', ''),
                'confidence': person.get('confidence', 0),
                'context': person.get('relationship_context', '')
            })
        return samples
