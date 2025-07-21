#!/usr/bin/env python3
"""
LLM-powered genealogy extractor using local models (Ollama)
"""

import json
import logging
import re
from pathlib import Path

import requests

from web_app.services.prompt_service import PromptService


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
        
        # Prompt service for getting active prompt from database
        self.prompt_service = PromptService()

        # Try to detect available LLM services
        self.check_ollama()

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
        """Create a specialized prompt for genealogical data extraction using active database prompt"""
        try:
            active_prompt = self.prompt_service.get_active_prompt()
            if active_prompt:
                # Replace the {text_chunk} placeholder with actual text
                return active_prompt.prompt_text.replace("{text_chunk}", text_chunk)
            else:
                logger.warning("No active prompt found, ensure default prompts are loaded")
                # Fallback to a basic prompt if no active prompt exists
                return f"Extract genealogical data from this Dutch text: {text_chunk}. Return JSON with families and isolated_individuals arrays."
        except Exception as e:
            logger.error(f"Failed to get active prompt from database: {e}")
            # Fallback to basic prompt on error
            return f"Extract genealogical data from this Dutch text: {text_chunk}. Return JSON with families and isolated_individuals arrays."

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


