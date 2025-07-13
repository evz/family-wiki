"""
OCR service for both CLI and web interface
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pdf_processing"))

from ocr_processor import PDFOCRProcessor
from shared_genealogy.logging_config import get_project_logger

logger = get_project_logger(__name__)

class OCRService:
    """Service for managing OCR processing"""
    
    def __init__(self):
        self.logger = get_project_logger(__name__)
    
    def process_pdfs(self, progress_callback: Callable = None) -> Dict:
        """Process all PDFs with OCR"""
        try:
            self.logger.info("Starting OCR processing")
            
            processor = PDFOCRProcessor()
            
            if progress_callback:
                progress_callback({"status": "starting", "message": "Initializing OCR processor"})
            
            # Process all PDFs
            results = processor.process_all_pdfs()
            
            if progress_callback:
                progress_callback({"status": "completed", "results": results})
            
            self.logger.info("OCR processing completed successfully")
            
            return {
                "success": True,
                "message": "OCR processing completed",
                "results": results
            }
            
        except Exception as e:
            error_msg = f"OCR processing failed: {str(e)}"
            self.logger.error(error_msg)
            
            if progress_callback:
                progress_callback({"status": "failed", "error": error_msg})
            
            return {
                "success": False,
                "error": error_msg
            }

# Global service instance
ocr_service = OCRService()