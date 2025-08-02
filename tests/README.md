# Family Wiki Tests

## PostgreSQL Requirement

**All tests require PostgreSQL to be running.** There is no SQLite fallback because the core business logic depends on PostgreSQL-specific features:

- **pgvector extension** - Vector embeddings for semantic search
- **TSVECTOR** - Full-text search functionality  
- **pg_trgm extension** - Trigram similarity matching
- **PostgreSQL arrays** - Daitch-Mokotoff soundex codes
- **Complex CTEs** - Hybrid search with Reciprocal Rank Fusion

## Running Tests

### 1. Start PostgreSQL (Required)

```bash
# Option A: Use setup script (recommended)
./setup-test-db.sh

# Option B: Manual setup
docker-compose up -d db
```

### 2. Run Tests

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_rag_service.py -v
pytest tests/test_models.py -v

# Run with coverage
pytest --cov=web_app --cov-report=html --cov-report=term-missing
```

## Troubleshooting

### "PostgreSQL test database not available"

This error means PostgreSQL is not running or the test database doesn't exist.

**Solution:**
```bash
./setup-test-db.sh
```

### "Connection refused"

PostgreSQL container is not running.

**Solution:**
```bash
docker-compose up -d db
# Wait for container to be ready, then:
./setup-test-db.sh
```

### Database connection issues

Check that PostgreSQL is listening on localhost:5432:

```bash
docker-compose ps db
docker-compose logs db
```

## Test Database

- **Database name:** `family_wiki_test`
- **User:** `family_wiki_user` 
- **Password:** `family_wiki_password`
- **Host:** `localhost:5432`

The test database is automatically created and configured with required extensions:
- `uuid-ossp`
- `vector` (pgvector)
- `pg_trgm`