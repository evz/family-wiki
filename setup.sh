#!/bin/bash

# Setup script for OCR processing environment

echo "Setting up OCR processing environment..."

# Install system dependencies if needed
echo "You may need to install these system packages:"
echo "sudo apt install python3.12-venv tesseract-ocr tesseract-ocr-nld tesseract-ocr-eng"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install -r requirements.txt

echo "Setup complete!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To run OCR processing: python ocr_processor.py"