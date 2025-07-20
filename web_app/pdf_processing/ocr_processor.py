#!/usr/bin/env python3
"""
OCR processor for family book PDFs with rotation detection and Dutch/English support
"""

import logging
import os
import tempfile
import time
from io import BytesIO
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from langdetect import LangDetectException, detect
from PIL import Image, ImageOps

from web_app.database import db
from web_app.database.models import OcrPage


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFOCRProcessor:
    def __init__(self, output_dir: str = "extracted_text"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Configure Tesseract for Dutch and English
        self.tesseract_config = '--oem 3 --psm 6 -l nld+eng'

    def detect_text_orientation(self, image: Image.Image) -> int:
        """Detect if text is upside down and return rotation angle needed"""
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

        # Try OCR with orientation detection
        try:
            # Get orientation info from Tesseract
            osd_config = '--psm 0 -l nld+eng'
            osd_data = pytesseract.image_to_osd(gray, config=osd_config)

            # Parse orientation data
            for line in osd_data.split('\n'):
                if 'Rotate:' in line:
                    rotation = int(line.split(':')[1].strip())
                    logger.info(f"Detected rotation: {rotation} degrees")
                    return rotation
        except Exception as e:
            logger.warning(f"Could not detect orientation, trying confidence method: {e}")

        # Fallback: try different rotations and pick the one with highest confidence
        best_rotation = 0
        best_confidence = 0

        for rotation in [0, 90, 180, 270]:
            try:
                rotated = image.rotate(rotation, expand=True)
                cv_rotated = cv2.cvtColor(np.array(rotated), cv2.COLOR_RGB2BGR)
                gray_rotated = cv2.cvtColor(cv_rotated, cv2.COLOR_BGR2GRAY)

                # Get confidence data
                data = pytesseract.image_to_data(gray_rotated, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]

                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    logger.info(f"Rotation {rotation}°: avg confidence {avg_confidence:.1f}")

                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_rotation = rotation

            except Exception as e:
                logger.warning(f"Error testing rotation {rotation}: {e}")
                continue

        logger.info(f"Best rotation: {best_rotation}° (confidence: {best_confidence:.1f})")
        return best_rotation

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from a PIL Image using OCR"""
        try:
            # Detect and correct orientation
            rotation = self.detect_text_orientation(image)
            if rotation != 0:
                image = image.rotate(rotation, expand=True)
                logger.info(f"Rotated image by {rotation} degrees")

            # Enhance image for better OCR
            image = ImageOps.grayscale(image)
            image = ImageOps.autocontrast(image)

            # Extract text
            text = pytesseract.image_to_string(image, config=self.tesseract_config)
            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""

    def process_pdf(self, pdf_path: Path) -> str:
        """Process a single PDF file and extract text from all pages"""
        logger.info(f"Processing PDF: {pdf_path.name}")

        try:
            pdf_document = fitz.open(str(pdf_path))
            all_text = []

            for page_num in range(len(pdf_document)):
                logger.info(f"Processing page {page_num + 1}/{len(pdf_document)}")

                page = pdf_document.load_page(page_num)

                # Convert page to image
                mat = fitz.Matrix(2, 2)  # 2x scale for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")

                # Create PIL Image
                with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as temp_file:
                    temp_file.write(img_data)
                    temp_file.flush()

                    image = Image.open(temp_file.name)
                    text = self.extract_text_from_image(image)

                    if text:
                        all_text.append(f"=== PAGE {page_num + 1} ===\n{text}\n")

                    os.unlink(temp_file.name)

            pdf_document.close()

            return "\n".join(all_text)

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return ""

    def process_all_pdfs(self, pdf_dir: Path) -> None:
        """Process all numbered PDFs in the directory"""
        pdf_files = sorted([f for f in pdf_dir.glob("*.pdf") if f.name.replace('.pdf', '').isdigit()])

        logger.info(f"Found {len(pdf_files)} numbered PDF files to process")

        for pdf_file in pdf_files:
            logger.info(f"Processing {pdf_file.name}...")

            text = self.process_pdf(pdf_file)

            if text:
                # Save extracted text
                output_file = self.output_dir / f"{pdf_file.stem}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Saved text to {output_file}")
            else:
                logger.warning(f"No text extracted from {pdf_file.name}")

        # Create consolidated file
        self.create_consolidated_text()

    def create_consolidated_text(self) -> None:
        """Combine all extracted text files into one consolidated file"""
        logger.info("Creating consolidated text file...")

        txt_files = sorted(self.output_dir.glob("*.txt"),
                          key=lambda x: int(x.stem) if x.stem.isdigit() else float('inf'))

        consolidated_path = self.output_dir / "consolidated_text.txt"

        with open(consolidated_path, 'w', encoding='utf-8') as consolidated:
            consolidated.write("FAMILY BOOK - CONSOLIDATED TEXT\n")
            consolidated.write("=" * 50 + "\n\n")

            for txt_file in txt_files:
                if txt_file.name != "consolidated_text.txt":
                    with open(txt_file, encoding='utf-8') as f:
                        consolidated.write(f"### FILE: {txt_file.name} ###\n")
                        consolidated.write(f.read())
                        consolidated.write("\n" + "="*50 + "\n\n")

        logger.info(f"Consolidated text saved to {consolidated_path}")

    def process_single_page_pdf_to_database(self, pdf_path: Path, batch_id: str, page_number: int = None) -> dict:
        """Process a single-page PDF and save to database"""
        logger.info(f"Processing single-page PDF to database: {pdf_path.name}")

        page_number = self._extract_page_number(pdf_path, page_number)
        start_time = time.time()

        # Convert PDF to image
        image_result = self._pdf_to_image(pdf_path, batch_id, page_number)
        if not image_result['success']:
            return image_result

        # Extract text from image
        text_result = self._extract_text_from_image(image_result['image'], batch_id, pdf_path.name, page_number)
        if not text_result['success']:
            return text_result

        # Save to database
        processing_time = int((time.time() - start_time) * 1000)
        return self._save_ocr_result(
            batch_id, pdf_path, page_number,
            text_result['text'], text_result['confidence'], text_result['language'],
            processing_time
        )

    def _extract_page_number(self, pdf_path: Path, page_number: int = None) -> int:
        """Extract page number from filename if not provided"""
        if page_number is not None:
            return page_number

        try:
            return int(pdf_path.stem)
        except ValueError:
            logger.warning(f"Could not extract page number from {pdf_path.name}, defaulting to 1")
            return 1

    def _pdf_to_image(self, pdf_path: Path, batch_id: str, page_number: int) -> dict:
        """Convert single-page PDF to PIL Image"""
        try:
            pdf_document = fitz.open(str(pdf_path))
        except (fitz.FileNotFoundError, fitz.FileDataError) as e:
            return self._save_ocr_error(batch_id, pdf_path.name, page_number, f"Invalid PDF file: {e}")

        if len(pdf_document) != 1:
            pdf_document.close()
            return self._save_ocr_error(batch_id, pdf_path.name, page_number,
                                      f"PDF must contain exactly 1 page, found {len(pdf_document)} pages")

        try:
            page = pdf_document.load_page(0)
            mat = fitz.Matrix(2, 2)  # 2x scale for better quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            image = Image.open(BytesIO(img_data))

            return {'success': True, 'image': image}

        except (RuntimeError, OSError) as e:
            return self._save_ocr_error(batch_id, pdf_path.name, page_number, f"Image conversion failed: {e}")
        finally:
            pdf_document.close()

    def _extract_text_from_image(self, image: Image, batch_id: str, filename: str, page_number: int) -> dict:
        """Extract text and metadata from PIL Image"""
        try:
            ocr_data = pytesseract.image_to_data(image, lang='nld+eng', output_type=pytesseract.Output.DICT)

            text_parts = []
            confidences = []

            for i, word in enumerate(ocr_data['text']):
                if word.strip():
                    text_parts.append(word)
                    confidences.append(int(ocr_data['conf'][i]))

            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Detect language
            detected_lang = self._detect_language(text)

            return {
                'success': True,
                'text': text,
                'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
                'language': detected_lang
            }

        except pytesseract.TesseractError as e:
            return self._save_ocr_error(batch_id, filename, page_number, f"OCR processing failed: {e}")

    def _detect_language(self, text: str) -> str:
        """Detect language of extracted text"""
        if not text or len(text.strip()) < 10:
            return 'unknown'

        try:
            return detect(text)
        except LangDetectException:
            return 'unknown'  # Cannot determine language

    def _save_ocr_result(self, batch_id: str, pdf_path: Path, page_number: int,
                        text: str, confidence: float, language: str, processing_time: int) -> dict:
        """Save successful OCR result to database"""
        try:
            existing = OcrPage.query.filter_by(batch_id=batch_id, filename=pdf_path.name).first()

            if existing:
                existing.extracted_text = text
                existing.confidence_score = confidence
                existing.language = language
                existing.processing_time_ms = processing_time
                existing.status = 'completed'
                existing.error_message = None
            else:
                ocr_page = OcrPage(
                    batch_id=batch_id,
                    filename=pdf_path.name,
                    page_number=page_number,
                    file_path=str(pdf_path),
                    extracted_text=text,
                    confidence_score=confidence,
                    ocr_engine='tesseract',
                    language=language,
                    processing_time_ms=processing_time,
                    status='completed'
                )
                db.session.add(ocr_page)

            db.session.commit()

            return {
                'success': True,
                'filename': pdf_path.name,
                'page_number': page_number,
                'batch_id': batch_id,
                'text_length': len(text),
                'confidence_score': confidence,
                'language': language,
                'processing_time_ms': processing_time
            }

        except Exception as e:
            db.session.rollback()
            return self._save_ocr_error(batch_id, pdf_path.name, page_number, f"Database error: {e}")

    def _save_ocr_error(self, batch_id: str, filename: str, page_number: int, error_message: str) -> dict:
        """Save OCR error to database"""
        logger.error(f"OCR error for {filename}: {error_message}")

        try:
            existing = OcrPage.query.filter_by(batch_id=batch_id, filename=filename).first()

            if existing:
                existing.status = 'failed'
                existing.error_message = error_message
            else:
                ocr_page = OcrPage(
                    batch_id=batch_id,
                    filename=filename,
                    page_number=page_number,
                    status='failed',
                    error_message=error_message
                )
                db.session.add(ocr_page)

            db.session.commit()
        except Exception as db_error:
            logger.error(f"Failed to save error to database: {db_error}")
            db.session.rollback()

        return {
            'success': False,
            'filename': filename,
            'page_number': page_number,
            'batch_id': batch_id,
            'error': error_message
        }

