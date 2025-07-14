"""
OCR service for both CLI and web interface
"""

from collections.abc import Callable

from web_app.pdf_processing.ocr_processor import PDFOCRProcessor
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

class OCRService:
    """Service for managing OCR processing"""

    def __init__(self):
        self.logger = get_project_logger(__name__)

    def process_pdfs(self, progress_callback: Callable = None) -> dict:
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
