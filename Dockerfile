FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libfontconfig1 \
        libice6 \
        tesseract-ocr \
        tesseract-ocr-nld \
        libtesseract-dev \
        poppler-utils \
        libpoppler-dev \
        libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory structure
RUN mkdir -p web_app/pdf_processing/pdfs \
    && mkdir -p web_app/pdf_processing/extracted_text \
    && mkdir -p logs \
    && mkdir -p templates \
    && mkdir -p web_app/static

# Copy Docker scripts first
COPY docker/ ./docker/
RUN chmod +x docker/*.sh

# Copy application files (this will be overridden by bind mount in development)
COPY . .

# Expose port
EXPOSE 5000

# Use the proper entrypoint script
CMD ["./docker/entrypoint.dev.sh"]