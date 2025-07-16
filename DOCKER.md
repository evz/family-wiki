# Docker Setup for Family Wiki

This document explains how to run the Family Wiki application using Docker and Docker Compose.

## Prerequisites

- Docker 20.10+ (with Docker Compose V2 integrated)
- External Ollama server (running on your network)

**Note:** Modern Docker includes Compose as a subcommand (`docker compose`). If you have an older installation with the standalone `docker-compose` command, consider upgrading to Docker Desktop or the latest Docker Engine.

**Docker Compose V2 Changes:**
- Uses `docker compose` instead of `docker-compose`
- The `version` field in compose files is now obsolete and has been removed
- All functionality remains the same, just modernized syntax

## Quick Start

### 1. Environment Setup

Copy the example environment file and customize it:

```bash
cp .env.example .env
# Edit .env to match your configuration, especially:
# - OLLAMA_HOST (your Ollama server IP)
# - SECRET_KEY (for production)
# - Database passwords
```

### 2. Development Environment

```bash
# Start development environment
make dev

# Or manually:
docker compose up -d
```

The application will be available at: http://localhost:5000

### 3. Production Environment

```bash
# Start production environment
make prod

# Or manually:
docker compose -f docker-compose.prod.yml up -d
```

## Architecture

### Services

1. **PostgreSQL Database (`db`)**
   - Image: `pgvector/pgvector:pg16`
   - Includes pgvector extension for RAG functionality
   - Persistent volume for data storage
   - Health checks for reliable startup

2. **Flask Web Application (`web`)**
   - Built from local Dockerfile
   - Connects to PostgreSQL database
   - Communicates with external Ollama server
   - Development: Hot-reload with volume mounts
   - Production: Optimized with gunicorn

3. **Nginx (Production Only)**
   - Reverse proxy and SSL termination
   - Only enabled with `--profile with-nginx`

### Volumes

- `postgres_data` - Database storage
- `app_uploads` - PDF files for processing
- `app_extracted` - Extracted text files
- `app_logs` - Application logs (production)

### Networks

- `family-wiki-network` - Internal bridge network for service communication

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```env
# Database
POSTGRES_DB=family_wiki
POSTGRES_USER=family_wiki_user
POSTGRES_PASSWORD=your-secure-password

# Flask
FLASK_ENV=development  # or production
SECRET_KEY=your-secret-key

# Ollama (External)
OLLAMA_HOST=192.168.1.234  # Your Ollama server IP
OLLAMA_PORT=11434
OLLAMA_MODEL=aya:35b-23
```

### Ollama Configuration

The application expects an external Ollama server. Make sure:

1. Ollama is running on your network
2. The required model is installed: `ollama pull aya:35b-23`
3. The OLLAMA_HOST points to the correct hostname or IP address
4. Firewall allows access to port 11434

**Network Hostname Resolution:**

If you're using a hostname for your Ollama server (like `the-area` instead of an IP address), the docker-compose files are configured to automatically map your `OLLAMA_HOST` to the Docker host using `host-gateway`. This allows containers to resolve local network hostnames that work on your host machine.

The configuration uses:
```yaml
extra_hosts:
  - "${OLLAMA_HOST}:host-gateway"
```

This means whatever hostname you set in your `.env` file for `OLLAMA_HOST` will be automatically resolvable from within the Docker containers.

## Usage

### Makefile Commands

```bash
# Development
make dev          # Start development environment
make build        # Build Docker images
make up           # Start services
make down         # Stop services
make restart      # Restart services
make logs         # View logs
make shell        # Access web container shell
make db-shell     # Access database shell

# Production
make prod         # Start production environment
make prod-build   # Build production images
make prod-down    # Stop production services

# Maintenance
make clean        # Clean up containers
make reset        # Reset everything (DESTRUCTIVE!)
make status       # Check service health
```

### Database Management

```bash
# Create backup
make db-backup

# Restore from backup
make db-restore file=backup_20240101_120000.sql

# Access database shell
make db-shell
```

### Script Permissions

**Important:** The entrypoint scripts in the `docker/` directory must be executable. If you're cloning the repository or the scripts lose their executable permissions, run:

```bash
chmod +x docker/*.sh
```

This is automatically handled in the Dockerfile, but may be needed if you modify the scripts locally.

### Manual Docker Commands

If you prefer manual control:

```bash
# Development
docker compose build
docker compose up -d
docker compose logs -f
docker compose down

# Production
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

## Development Workflow

1. **Start Environment**: `make dev`
2. **View Logs**: `make logs`
3. **Make Changes**: Edit code (auto-reloads in development)
4. **Access Shell**: `make shell` for debugging
5. **Database Access**: `make db-shell` for database work
6. **Stop Environment**: `make down`

## Production Deployment

### Basic Production Setup

1. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with production values:
   # - Set FLASK_ENV=production
   # - Set strong SECRET_KEY
   # - Set secure database passwords
   ```

2. **Deploy**:
   ```bash
   make prod
   ```

### With Nginx (SSL/HTTPS)

1. **Create nginx.conf** (example provided separately)
2. **Add SSL certificates** to `./ssl/` directory
3. **Deploy with Nginx**:
   ```bash
   docker compose -f docker-compose.prod.yml --profile with-nginx up -d
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database health
   docker compose exec db pg_isready -U family_wiki_user -d family_wiki
   
   # Check logs
   docker compose logs db
   ```

2. **Ollama Connection Issues**
   ```bash
   # Test Ollama connectivity from web container
   docker compose exec web curl http://192.168.1.234:11434/api/tags
   
   # Update OLLAMA_HOST in .env if needed
   ```

3. **OpenCV/Image Processing Library Issues**
   ```bash
   # Error: libGL.so.1: cannot open shared object file
   # This is fixed in the Dockerfiles with the required system libraries:
   # libgl1-mesa-glx, libglib2.0-0, libsm6, libxext6, libxrender1, 
   # libfontconfig1, libice6, tesseract-ocr, libtesseract-dev, etc.
   
   # If you still get OpenCV errors, rebuild the images:
   docker compose build --no-cache
   ```

4. **Permission Issues**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 web_app/pdf_processing/
   ```

5. **Port Conflicts**
   ```bash
   # Change ports in docker-compose.yml if 5000 or 5432 are in use
   ports:
     - "8080:5000"  # Use port 8080 instead of 5000
   ```

### Health Checks

```bash
# Check all services
make status

# Test web application
curl http://localhost:5000/api/status

# Test database
docker compose exec db pg_isready -U family_wiki_user -d family_wiki
```

### Logs and Debugging

```bash
# View all logs
make logs

# View specific service logs
docker compose logs web
docker compose logs db

# Access container for debugging
make shell
```

## Data Persistence

- **Database**: Stored in `postgres_data` volume
- **Uploaded PDFs**: Stored in `app_uploads` volume  
- **Extracted Text**: Stored in `app_extracted` volume
- **Application Logs**: Stored in `app_logs` volume (production)

To backup all data:
```bash
# Create full backup
docker run --rm -v family-wiki_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
docker run --rm -v family-wiki_app_uploads:/data -v $(pwd):/backup ubuntu tar czf /backup/uploads_backup.tar.gz /data
```

## Security Considerations

1. **Change default passwords** in `.env`
2. **Use strong SECRET_KEY** for production
3. **Secure Ollama server** with proper network configuration
4. **Regular backups** of database and upload volumes
5. **Monitor logs** for security issues
6. **Use HTTPS** in production with proper SSL certificates

## Performance Tuning

1. **Database**: Adjust PostgreSQL configuration in `init-db.sql`
2. **Web Server**: Modify gunicorn workers in `Dockerfile.prod`
3. **Resources**: Set Docker memory/CPU limits if needed
4. **Volumes**: Use faster storage for database volume

## Monitoring

Consider adding monitoring services:

```yaml
# Add to docker-compose.yml
  prometheus:
    image: prom/prometheus
    # ... configuration

  grafana:
    image: grafana/grafana
    # ... configuration
```

For production monitoring, consider tools like:
- Prometheus + Grafana
- ELK Stack for log analysis
- Health check endpoints
- Resource monitoring