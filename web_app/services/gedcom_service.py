"""
GEDCOM service for both CLI and web interface
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gedcom_generator import LLMGEDCOMGenerator
from shared_genealogy.logging_config import get_project_logger

logger = get_project_logger(__name__)

class GedcomService:
    """Service for managing GEDCOM generation"""
    
    def __init__(self):
        self.logger = get_project_logger(__name__)
    
    def generate_gedcom(self, input_file: str = None, output_file: str = None, progress_callback: Callable = None) -> Dict:
        """Generate GEDCOM file from extraction results"""
        try:
            self.logger.info("Starting GEDCOM generation")
            
            if progress_callback:
                progress_callback({"status": "starting", "message": "Initializing GEDCOM generator"})
            
            # Use default files if not specified
            input_file = input_file or "pdf_processing/llm_genealogy_results.json"
            output_file = output_file or "family_genealogy.ged"
            
            generator = LLMGEDCOMGenerator(input_file, output_file)
            
            if progress_callback:
                progress_callback({"status": "running", "message": "Processing family data"})
            
            # Generate GEDCOM
            results = generator.generate()
            
            if progress_callback:
                progress_callback({"status": "completed", "results": results})
            
            self.logger.info("GEDCOM generation completed successfully")
            
            return {
                "success": True,
                "message": "GEDCOM generation completed",
                "output_file": output_file,
                "results": results
            }
            
        except Exception as e:
            error_msg = f"GEDCOM generation failed: {str(e)}"
            self.logger.error(error_msg)
            
            if progress_callback:
                progress_callback({"status": "failed", "error": error_msg})
            
            return {
                "success": False,
                "error": error_msg
            }

# Global service instance
gedcom_service = GedcomService()