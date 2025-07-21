"""
Tests for OCR processor database integration
"""

import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytesseract
import pytest
from langdetect import LangDetectException

from web_app.database import db
from web_app.database.models import OcrPage
from web_app.pdf_processing.ocr_processor import PDFOCRProcessor


class TestOCRDatabaseIntegration:
    """Test OCR processor database integration"""

    @pytest.fixture
    def processor(self):
        """Create OCR processor instance"""
        return PDFOCRProcessor()

    @pytest.fixture
    def sample_batch_id(self):
        """Generate sample batch ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def clean_db(self, db):
        """Clean database before each test"""
        OcrPage.query.delete()
        db.session.commit()
        yield
        OcrPage.query.delete()
        db.session.commit()

    def test_extract_page_number_from_filename(self, processor):
        """Test page number extraction from filename"""
        # Test numeric filename
        pdf_path = Path("001.pdf")
        assert processor._extract_page_number(pdf_path) == 1

        pdf_path = Path("042.pdf")
        assert processor._extract_page_number(pdf_path) == 42

        # Test non-numeric filename (should default to 1)
        pdf_path = Path("document.pdf")
        assert processor._extract_page_number(pdf_path) == 1

        # Test explicit page number override
        pdf_path = Path("001.pdf")
        assert processor._extract_page_number(pdf_path, page_number=5) == 5

    def test_detect_language_dutch(self, processor):
        """Test language detection for Dutch text"""
        dutch_text = "Dit is een Nederlandse tekst over genealogie van de familie"
        result = processor._detect_language(dutch_text)
        assert result == 'nl'

    def test_detect_language_english(self, processor):
        """Test language detection for English text"""
        english_text = "This is an English text about family genealogy and history"
        result = processor._detect_language(english_text)
        assert result == 'en'

    def test_detect_language_short_text(self, processor):
        """Test language detection for short text"""
        short_text = "Test"
        result = processor._detect_language(short_text)
        assert result == 'unknown'

    def test_detect_language_empty_text(self, processor):
        """Test language detection for empty text"""
        assert processor._detect_language("") == 'unknown'
        assert processor._detect_language(None) == 'unknown'

    @patch('web_app.pdf_processing.ocr_processor.detect')
    def test_detect_language_fallback(self, mock_detect, processor):
        """Test language detection fallback on error"""
        mock_detect.side_effect = LangDetectException("ERROR", "Detection error")

        result = processor._detect_language("Some text that causes detection error")
        assert result == 'unknown'

    @patch('web_app.pdf_processing.ocr_processor.fitz')
    def test_pdf_to_image_invalid_file(self, mock_fitz, processor, sample_batch_id):
        """Test PDF to image conversion with invalid file"""
        mock_fitz.open.side_effect = mock_fitz.FileNotFoundError("File not found")

        pdf_path = Path("nonexistent.pdf")
        result = processor._pdf_to_image(pdf_path, sample_batch_id, 1)

        assert result['success'] is False
        assert 'Invalid PDF file' in result['error']

    @patch('web_app.pdf_processing.ocr_processor.fitz')
    def test_pdf_to_image_multiple_pages(self, mock_fitz, processor, sample_batch_id):
        """Test PDF to image conversion with multiple pages"""
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=2)  # Multiple pages
        mock_fitz.open.return_value = mock_doc

        pdf_path = Path("multipage.pdf")
        result = processor._pdf_to_image(pdf_path, sample_batch_id, 1)

        assert result['success'] is False
        assert 'must contain exactly 1 page' in result['error']
        mock_doc.close.assert_called_once()

    @patch('web_app.pdf_processing.ocr_processor.fitz')
    @patch('web_app.pdf_processing.ocr_processor.Image')
    def test_pdf_to_image_success(self, mock_image, mock_fitz, processor, sample_batch_id):
        """Test successful PDF to image conversion"""
        # Mock PDF document
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_page = Mock()
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        # Mock pixmap
        mock_pix = Mock()
        mock_pix.tobytes.return_value = b"fake_image_data"
        mock_page.get_pixmap.return_value = mock_pix

        # Mock PIL Image
        mock_image_obj = Mock()
        mock_image.open.return_value = mock_image_obj

        pdf_path = Path("001.pdf")
        result = processor._pdf_to_image(pdf_path, sample_batch_id, 1)

        assert result['success'] is True
        assert result['image'] == mock_image_obj
        mock_doc.close.assert_called_once()

    @patch('web_app.pdf_processing.ocr_processor.pytesseract')
    def test_extract_text_from_image_success(self, mock_tesseract, processor, sample_batch_id):
        """Test successful text extraction from image"""
        # Mock OCR data
        mock_tesseract.image_to_data.return_value = {
            'text': ['This', 'is', 'test', 'text', '', ''],
            'conf': [95, 90, 85, 92, -1, -1]  # -1 for empty strings
        }

        mock_image = Mock()
        result = processor._extract_text_from_image(mock_image, sample_batch_id, "test.pdf", 1)

        assert result['success'] is True
        assert result['text'] == 'This is test text'
        assert 0.90 <= result['confidence'] <= 0.92  # Average of [95, 90, 85, 92] / 100
        assert result['language'] in ['en', 'unknown']  # Depends on text length

    @patch('web_app.pdf_processing.ocr_processor.pytesseract')
    def test_extract_text_from_image_tesseract_error(self, mock_tesseract, processor, sample_batch_id, clean_db):
        """Test text extraction with Tesseract error"""
        mock_tesseract.TesseractError = pytesseract.TesseractError
        mock_tesseract.image_to_data.side_effect = pytesseract.TesseractError(1, "OCR failed")

        mock_image = Mock()
        result = processor._extract_text_from_image(mock_image, sample_batch_id, "test.pdf", 1)

        assert result['success'] is False
        assert 'OCR processing failed' in result['error']

    def test_save_ocr_result_new_record(self, processor, sample_batch_id, clean_db):
        """Test saving new OCR result to database"""
        pdf_path = Path("001.pdf")

        result = processor._save_ocr_result(
            sample_batch_id, pdf_path, 1,
            "Test text", 0.95, "en", 1500
        )

        assert result['success'] is True
        assert result['filename'] == "001.pdf"
        assert result['confidence_score'] == 0.95

        # Verify database record
        ocr_page = OcrPage.query.filter_by(batch_id=sample_batch_id, filename="001.pdf").first()
        assert ocr_page is not None
        assert ocr_page.extracted_text == "Test text"
        assert ocr_page.confidence_score == 0.95
        assert ocr_page.language == "en"
        assert ocr_page.status == "completed"

    def test_save_ocr_result_update_existing(self, processor, sample_batch_id, clean_db):
        """Test updating existing OCR result in database"""
        # Create initial record
        ocr_page = OcrPage(
            batch_id=sample_batch_id,
            filename="001.pdf",
            page_number=1,
            extracted_text="Old text",
            confidence_score=0.5,
            language="unknown",
            status="completed"
        )
        db.session.add(ocr_page)
        db.session.commit()

        # Update with new data
        pdf_path = Path("001.pdf")
        result = processor._save_ocr_result(
            sample_batch_id, pdf_path, 1,
            "New text", 0.95, "en", 1500
        )

        assert result['success'] is True

        # Verify update
        updated = OcrPage.query.filter_by(batch_id=sample_batch_id, filename="001.pdf").first()
        assert updated.extracted_text == "New text"
        assert updated.confidence_score == 0.95
        assert updated.language == "en"

    def test_save_ocr_error(self, processor, sample_batch_id, clean_db):
        """Test saving OCR error to database"""
        result = processor._save_ocr_error(sample_batch_id, "failed.pdf", 1, "Test error message")

        assert result['success'] is False
        assert result['error'] == "Test error message"

        # Verify error record in database
        ocr_page = OcrPage.query.filter_by(batch_id=sample_batch_id, filename="failed.pdf").first()
        assert ocr_page is not None
        assert ocr_page.status == "failed"
        assert ocr_page.error_message == "Test error message"

    @patch.object(PDFOCRProcessor, '_pdf_to_image')
    @patch.object(PDFOCRProcessor, '_extract_text_from_image')
    @patch.object(PDFOCRProcessor, '_save_ocr_result')
    def test_process_single_page_pdf_success_flow(self, mock_save, mock_extract, mock_pdf_to_image,
                                                  processor, sample_batch_id):
        """Test successful end-to-end PDF processing flow"""
        # Mock successful image conversion
        mock_pdf_to_image.return_value = {'success': True, 'image': Mock()}

        # Mock successful text extraction
        mock_extract.return_value = {
            'success': True,
            'text': 'Test text',
            'confidence': 0.95,
            'language': 'en'
        }

        # Mock successful save
        mock_save.return_value = {'success': True}

        pdf_path = Path("001.pdf")
        result = processor.process_single_page_pdf_to_database(pdf_path, sample_batch_id)

        assert result['success'] is True
        mock_pdf_to_image.assert_called_once()
        mock_extract.assert_called_once()
        mock_save.assert_called_once()

    @patch.object(PDFOCRProcessor, '_pdf_to_image')
    def test_process_single_page_pdf_image_conversion_failure(self, mock_pdf_to_image,
                                                             processor, sample_batch_id):
        """Test PDF processing with image conversion failure"""
        mock_pdf_to_image.return_value = {'success': False, 'error': 'Image conversion failed'}

        pdf_path = Path("001.pdf")
        result = processor.process_single_page_pdf_to_database(pdf_path, sample_batch_id)

        assert result['success'] is False
        assert result['error'] == 'Image conversion failed'
