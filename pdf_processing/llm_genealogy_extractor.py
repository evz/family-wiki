#!/usr/bin/env python3
"""
LLM-powered genealogy extractor using local models (Ollama) or OpenAI
"""

import json
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMGenealogyExtractor:
    def __init__(self, text_file: str = "extracted_text/consolidated_text.txt"):
        self.text_file = Path(text_file)
        self.results = []
        
        # Try to detect available LLM services
        self.check_ollama()
        self.check_openai()
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"Ollama available with {len(models)} models")
                return True
        except:
            logger.info("Ollama not available")
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
    
    def query_ollama(self, prompt: str, model: str = "qwen2.5:7b") -> Optional[str]:
        """Query Ollama local LLM"""
        try:
            response = requests.post("http://localhost:11434/api/generate", 
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
            logger.error(f"Ollama query failed: {e}")
        return None
    
    def create_genealogy_prompt(self, text_chunk: str) -> str:
        """Create a specialized prompt for genealogical data extraction"""
        return f"""You are an expert Dutch genealogist. Analyze this historical family record text and extract structured information about individuals.

IMPORTANT CONTEXT:
- This is Dutch genealogical text from a family book
- * means birth, ~ means baptism, + means death, x means marriage
- Letters like "a.", "b.", "c." indicate siblings in birth order
- Patterns like "1.1" or "III.2" indicate family groups
- Dutch place names and dates in DD.MM.YYYY format are common
- Names often include "van" (from) indicating place of origin

TEXT TO ANALYZE:
{text_chunk}

Extract information for each person mentioned and return ONLY valid JSON in this exact format:
[
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
    "parents": "parent names if mentioned",
    "sibling_letter": "letter like a, b, c if present",
    "notes": "any additional information",
    "confidence": 0.85
  }}
]

Rules:
- Only include people explicitly mentioned, not hypothetical ones
- Leave fields empty ("") if information is not clearly stated
- Use confidence 0.9+ only for very clear information
- Include Dutch names and places exactly as written
- If no clear individuals are found, return empty array []

JSON RESPONSE:"""
    
    def extract_from_chunk(self, text_chunk: str) -> List[Dict]:
        """Extract genealogical data from a text chunk using LLM"""
        prompt = self.create_genealogy_prompt(text_chunk)
        
        # Try Ollama first
        response = self.query_ollama(prompt)
        
        if not response:
            logger.warning("LLM extraction failed for chunk")
            return []
        
        try:
            # Try to parse JSON from response
            # Sometimes LLMs add extra text, so find the JSON part
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                people = json.loads(json_str)
                return people if isinstance(people, list) else []
            else:
                logger.warning("No JSON found in LLM response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response was: {response[:500]}...")
            return []
    
    def split_text_intelligently(self, text: str) -> List[str]:
        """Split text into meaningful chunks for LLM processing"""
        # Remove file markers and clean up
        text = re.sub(r'=== PAGE \d+ ===', '', text)
        text = re.sub(r'### FILE: \d+\.txt ###', '', text)
        text = re.sub(r'={20,}', '', text)
        
        chunks = []
        
        # Split by generation headers first
        generation_splits = re.split(r'(EERSTE|TWEEDE|DERDE|VIERDE|VIJFDE|ZESDE)\s+GENERATIE', text, flags=re.IGNORECASE)
        
        current_generation = ""
        for i, section in enumerate(generation_splits):
            section = section.strip()
            if not section:
                continue
            
            # Check if this is a generation header
            if re.match(r'(EERSTE|TWEEDE|DERDE|VIERDE|VIJFDE|ZESDE)', section, re.IGNORECASE):
                current_generation = section + " GENERATIE"
                continue
            
            # Split further by family groups or natural breaks
            family_splits = re.split(r'(\d+\.?\d*\.\s+Kinderen van [^:]+:)', section)
            
            for j, subsection in enumerate(family_splits):
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
        
        with open(self.text_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = self.split_text_intelligently(content)
        
        all_people = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            people = self.extract_from_chunk(chunk)
            
            # Add chunk metadata
            for person in people:
                person['chunk_id'] = i
                person['extraction_method'] = 'llm'
            
            all_people.extend(people)
            
            # Small delay to be nice to the LLM
            import time
            time.sleep(1)
        
        self.results = all_people
        logger.info(f"Extraction complete: found {len(all_people)} people")
    
    def save_results(self, output_file: str = "llm_genealogy_results.json") -> None:
        """Save LLM extraction results"""
        output_path = Path(output_file)
        
        data = {
            'metadata': {
                'total_people': len(self.results),
                'extraction_method': 'llm_powered',
                'model_used': 'ollama_llama3.1'
            },
            'people': self.results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_path}")
    
    def print_summary(self) -> None:
        """Print extraction summary"""
        print(f"\nLLM Genealogy Extraction Summary:")
        print(f"Total people extracted: {len(self.results)}")
        
        if self.results:
            # Confidence distribution
            confidences = [p.get('confidence', 0) for p in self.results]
            avg_confidence = sum(confidences) / len(confidences)
            print(f"Average confidence: {avg_confidence:.2f}")
            
            # Top results
            sorted_people = sorted(self.results, 
                                 key=lambda p: p.get('confidence', 0), 
                                 reverse=True)
            
            print(f"\nTop 15 extractions:")
            for person in sorted_people[:15]:
                name = f"{person.get('given_names', '')} {person.get('surname', '')}".strip()
                birth = f" *{person.get('birth_date', '')}" if person.get('birth_date') else ""
                spouse = f" x {person.get('spouse_name', '')}" if person.get('spouse_name') else ""
                conf = person.get('confidence', 0)
                print(f"  - {name}{birth}{spouse} (conf: {conf:.2f})")

def main():
    print("LLM-Powered Genealogy Extraction")
    print("=" * 40)
    print("This tool uses local LLMs (Ollama) to intelligently extract genealogical data.")
    print("Install Ollama and run 'ollama pull llama3.1' first.")
    print()
    
    extractor = LLMGenealogyExtractor()
    extractor.process_all_text()
    extractor.print_summary()
    extractor.save_results()
    
    print(f"\nResults saved! Review llm_genealogy_results.json")
    print(f"This approach should be much more accurate than regex parsing.")

if __name__ == "__main__":
    main()