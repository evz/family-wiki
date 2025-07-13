"""
Research service for both CLI and web interface
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from research_question_generator import ResearchQuestionGenerator
from shared_genealogy.logging_config import get_project_logger

logger = get_project_logger(__name__)

class ResearchService:
    """Service for managing research question generation"""
    
    def __init__(self):
        self.logger = get_project_logger(__name__)
    
    def generate_questions(self, input_file: str = None, progress_callback: Callable = None) -> Dict:
        """Generate research questions from family data"""
        try:
            self.logger.info("Starting research question generation")
            
            if progress_callback:
                progress_callback({"status": "starting", "message": "Initializing research generator"})
            
            # Use default file if not specified
            input_file = input_file or "pdf_processing/llm_genealogy_results.json"
            
            generator = ResearchQuestionGenerator(input_file)
            
            if progress_callback:
                progress_callback({"status": "running", "message": "Analyzing family data"})
            
            # Generate questions
            questions = generator.generate_questions()
            
            if progress_callback:
                progress_callback({"status": "completed", "results": {"questions": questions}})
            
            self.logger.info("Research question generation completed successfully")
            
            return {
                "success": True,
                "message": "Research questions generated",
                "questions": questions,
                "total_questions": len(questions)
            }
            
        except Exception as e:
            error_msg = f"Research question generation failed: {str(e)}"
            self.logger.error(error_msg)
            
            if progress_callback:
                progress_callback({"status": "failed", "error": error_msg})
            
            return {
                "success": False,
                "error": error_msg
            }

# Global service instance
research_service = ResearchService()