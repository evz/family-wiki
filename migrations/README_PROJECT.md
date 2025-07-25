# Database Migrations

This directory contains Flask-Migrate database migration files for the Family Wiki Tools project.

## Overview

Flask-Migrate uses Alembic to handle database schema changes. This ensures that database changes are applied consistently across development, testing, and production environments.

## Migration Process

### Creating New Migrations

When you modify the database models in `web_app/database/models.py`, create a new migration:

```bash
source .venv/bin/activate
export FLASK_APP=app.py
# Set your environment variables (see .env.example)
export DATABASE_URL=postgresql://family_wiki_user:family_wiki_password@localhost:5432/family_wiki
export SECRET_KEY=your-secret-key
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
export OLLAMA_HOST=localhost
export OLLAMA_PORT=11434
export OLLAMA_MODEL=aya:8b-23

# Generate the migration
flask db migrate -m "Description of your changes"

# Review the generated migration file in migrations/versions/
# Edit if necessary to fix any issues

# Apply the migration
flask db upgrade
```

### Applying Migrations

Migrations are automatically applied when the Docker containers start up via the entrypoint scripts.

For manual application:
```bash
flask db upgrade
```

### Migration History

- `804c62019e8c_initial_migration_with_gedcom_id_column.py` - Initial migration adding gedcom_id and sex columns to persons table, and batch_id to ocr_pages table

## Docker Integration

The Docker entrypoint scripts (`docker/entrypoint.dev.sh` and `docker/entrypoint.prod.sh`) automatically run `flask db upgrade` on container startup to ensure the database schema is up-to-date.

## Important Notes

- Always review generated migrations before applying them
- Test migrations on a copy of production data before deploying
- The custom UUID type in models.py may need manual adjustment in migration files
- Migrations are applied automatically in Docker containers