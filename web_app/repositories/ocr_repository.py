"""
Repository for OCR-related database operations
Follows the established repository pattern with proper transaction management
"""

from pathlib import Path
from typing import Union

from web_app.database.models import OcrPage
from web_app.repositories.base_repository import ModelRepository


class OcrRepository(ModelRepository[OcrPage]):
    """Repository for managing OCR page data in the database"""
    
    def __init__(self, db_session=None):
        """Initialize OCR repository"""
        super().__init__(OcrPage, db_session)
    
    def save_ocr_result(self, batch_id: str, pdf_path: Path, page_number: int,
                       text: str, confidence: float, language: str, processing_time: int) -> dict:
        """
        Save successful OCR result to database
        
        Args:
            batch_id: Batch identifier for this OCR operation
            pdf_path: Path to the PDF file that was processed
            page_number: Page number within the PDF
            text: Extracted text content
            confidence: OCR confidence score (0.0 to 1.0)
            language: Detected language code
            processing_time: Processing time in milliseconds
            
        Returns:
            dict: Success result with saved data
        """
        def _save_ocr_result():
            filename = pdf_path.name
            
            # Check for existing record
            existing = self.get_by_batch_and_filename(batch_id, filename)
            
            if existing:
                # Update existing record
                self.update(existing,
                           extracted_text=text,
                           confidence_score=confidence,
                           language=language,
                           processing_time_ms=processing_time,
                           status="completed",
                           error_message=None)
                ocr_page = existing
            else:
                # Create new record
                ocr_page = self.create(
                    batch_id=batch_id,
                    filename=filename,
                    page_number=page_number,
                    extracted_text=text,
                    confidence_score=confidence,
                    language=language,
                    processing_time_ms=processing_time,
                    status="completed"
                )
            
            return {
                'success': True,
                'filename': filename,
                'confidence_score': confidence,
                'language': language,
                'processing_time_ms': processing_time,
                'record_id': ocr_page.id
            }
        
        return self.safe_operation(_save_ocr_result, "save OCR result")
    
    def save_ocr_error(self, batch_id: str, filename: str, page_number: int, error_message: str) -> dict:
        """
        Save OCR error to database
        
        Args:
            batch_id: Batch identifier for this OCR operation
            filename: Name of the file that failed
            page_number: Page number that failed
            error_message: Error description
            
        Returns:
            dict: Error result with saved error data
        """
        def _save_ocr_error():
            # Check for existing record
            existing = self.get_by_batch_and_filename(batch_id, filename)
            
            if existing:
                # Update existing record with error
                self.update(existing,
                           status="failed",
                           error_message=error_message)
                ocr_page = existing
            else:
                # Create new error record
                ocr_page = self.create(
                    batch_id=batch_id,
                    filename=filename,
                    page_number=page_number,
                    status="failed",
                    error_message=error_message
                )
            
            self.logger.error(f"OCR error for {filename}: {error_message}")
            
            return {
                'success': False,
                'error': error_message,
                'filename': filename,
                'record_id': ocr_page.id
            }
        
        return self.safe_operation(_save_ocr_error, "save OCR error")
    
    def get_by_batch_and_filename(self, batch_id: str, filename: str) -> Union[OcrPage, None]:
        """Get OCR page by batch ID and filename"""
        def _get_by_batch_and_filename():
            return OcrPage.query.filter_by(batch_id=batch_id, filename=filename).first()
        
        return self.safe_query(_get_by_batch_and_filename, "get OCR page by batch and filename")
    
    def get_by_batch_id(self, batch_id: str) -> list[OcrPage]:
        """Get all OCR pages for a batch"""
        def _get_by_batch_id():
            return OcrPage.query.filter_by(batch_id=batch_id).order_by(OcrPage.page_number).all()
        
        return self.safe_query(_get_by_batch_id, "get OCR pages by batch ID")
    
    def get_batch_stats(self, batch_id: str) -> dict:
        """Get statistics for an OCR batch"""
        def _get_batch_stats():
            pages = self.get_by_batch_id(batch_id)
            
            if not pages:
                return {
                    'total_pages': 0,
                    'completed': 0,
                    'failed': 0,
                    'average_confidence': 0.0,
                    'total_processing_time': 0
                }
            
            completed_pages = [p for p in pages if p.status == "completed"]
            failed_pages = [p for p in pages if p.status == "failed"]
            
            # Calculate average confidence for completed pages
            avg_confidence = 0.0
            if completed_pages:
                confidences = [p.confidence_score for p in completed_pages if p.confidence_score is not None]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
            
            # Calculate total processing time
            total_time = sum(p.processing_time_ms or 0 for p in completed_pages)
            
            return {
                'total_pages': len(pages),
                'completed': len(completed_pages),
                'failed': len(failed_pages),
                'average_confidence': round(avg_confidence, 3),
                'total_processing_time': total_time
            }
        
        return self.safe_query(_get_batch_stats, "get OCR batch statistics")
    
    def clear_batch_data(self, batch_id: str) -> None:
        """Clear all OCR data for a specific batch"""
        def _clear_batch_data():
            deleted_count = OcrPage.query.filter_by(batch_id=batch_id).delete()
            self.logger.info(f"Cleared {deleted_count} OCR pages for batch {batch_id}")
            return deleted_count
        
        return self.safe_operation(_clear_batch_data, f"clear OCR batch {batch_id}")