#!/usr/bin/env python3
"""
OCR processor for family book PDFs with rotation detection and Dutch/English support
"""

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path


try:
    import cv2
    import fitz  # PyMuPDF
    import numpy as np
    import pytesseract
    from PIL import Image, ImageOps
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install PyMuPDF pytesseract pillow opencv-python")
    sys.exit(1)

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

def main():
    parser = argparse.ArgumentParser(description="OCR processor for family book PDFs")
    parser.add_argument("--pdf-dir", default="pdfs", help="Directory containing PDF files")
    parser.add_argument("--output-dir", default="extracted_text", help="Output directory for text files")
    parser.add_argument("--single-pdf", help="Process a single PDF file")

    args = parser.parse_args()

    processor = PDFOCRProcessor(args.output_dir)

    if args.single_pdf:
        pdf_path = Path(args.single_pdf)
        if pdf_path.exists():
            text = processor.process_pdf(pdf_path)
            output_file = processor.output_dir / f"{pdf_path.stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Text extracted to {output_file}")
        else:
            print(f"PDF file not found: {pdf_path}")
    else:
        pdf_dir = Path(args.pdf_dir)
        if pdf_dir.exists():
            processor.process_all_pdfs(pdf_dir)
        else:
            print(f"PDF directory not found: {pdf_dir}")

if __name__ == "__main__":
    main()
