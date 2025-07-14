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

# Copy application files (this will be overridden by bind mount in development)
COPY . .

# Expose port
EXPOSE 5000

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "Waiting for PostgreSQL..."\n\
while ! pg_isready -h db -p 5432; do\n\
  sleep 1\n\
done\n\
echo "PostgreSQL is ready!"\n\
\n\
# Initialize database tables\n\
python -c "from app import create_app; app = create_app(); app.app_context().push(); from web_app.database import db; db.create_all(); print(\"Database tables created!\")"\n\
\n\
# Start Flask in debug mode\n\
flask run --host=0.0.0.0 --debug' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]