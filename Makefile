.PHONY: help build up down logs shell db-shell clean restart dev prod

# Default target
help:
	@echo "Family Wiki Docker Management"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev          - Start development environment"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start services"
	@echo "  make down         - Stop services"
	@echo "  make restart      - Restart services"
	@echo "  make logs         - View logs"
	@echo "  make shell        - Access web container shell"
	@echo "  make db-shell     - Access database shell"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-build   - Build production images"
	@echo "  make prod-down    - Stop production services"
	@echo "  make prod-logs    - View production logs"
	@echo ""
	@echo "Health & Monitoring:"
	@echo "  make status       - Check service status and health"
	@echo "  make health-web   - Run web application health check"
	@echo "  make health-db    - Run database health check"
	@echo ""
	@echo "Development Utilities:"
	@echo "  make dev-shell    - Open shell in web container"
	@echo "  make dev-logs-web - Follow web container logs"
	@echo "  make dev-logs-db  - Follow database logs"
	@echo "  make build-web    - Build only web container"
	@echo "  make build-db     - Pull database image"
	@echo ""
	@echo "Database Management:"
	@echo "  make db-backup    - Create database backup"
	@echo "  make db-restore   - Restore database (Usage: make db-restore file=backup.sql)"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  make clean        - Clean up containers and volumes"
	@echo "  make reset        - Reset everything (destructive!)"

# Development environment
dev: build up

build:
	@echo "Building Docker images..."
	docker compose build

up:
	@echo "Starting development environment..."
	docker compose up -d
	@echo "Services started. Web app available at http://localhost:5000"

down:
	@echo "Stopping services..."
	docker compose down

restart: down up

logs:
	docker compose logs -f

shell:
	docker compose exec web bash

db-shell:
	docker compose exec db psql -U family_wiki_user -d family_wiki

# Production environment
prod: prod-build
	@echo "Starting production environment..."
	docker compose -f docker-compose.prod.yml up -d
	@echo "Production services started."

prod-build:
	@echo "Building production Docker images..."
	docker compose -f docker-compose.prod.yml build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

# Maintenance
clean:
	@echo "Cleaning up containers..."
	docker compose down
	docker compose -f docker-compose.prod.yml down 2>/dev/null || true
	docker system prune -f

reset:
	@echo "WARNING: This will delete all data! Press Ctrl+C to cancel."
	@sleep 5
	docker compose down -v
	docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
	docker system prune -a -f --volumes

# Database management
db-backup:
	@echo "Creating database backup..."
	docker compose exec db pg_dump -U family_wiki_user family_wiki > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore:
	@if [ -z "$(file)" ]; then echo "Usage: make db-restore file=backup.sql"; exit 1; fi
	@echo "Restoring database from $(file)..."
	docker compose exec -T db psql -U family_wiki_user family_wiki < $(file)

# Health check
status:
	@echo "Service Status:"
	@docker compose ps
	@echo ""
	@echo "Detailed Health Checks:"
	@docker compose exec web ./docker/healthcheck.sh || echo "Web health check failed"

# Individual health checks
health-web:
	@echo "Running web application health check..."
	@docker compose exec web ./docker/healthcheck.sh

health-db:
	@echo "Running database health check..."
	@docker compose exec db pg_isready -U family_wiki_user -d family_wiki

# Development utilities
dev-shell:
	@echo "Opening shell in development web container..."
	@docker compose exec web bash

dev-logs-web:
	@echo "Following web container logs..."
	@docker compose logs -f web

dev-logs-db:
	@echo "Following database container logs..."
	@docker compose logs -f db

# Build specific services
build-web:
	@echo "Building web container..."
	@docker compose build web

build-db:
	@echo "Pulling database image..."
	@docker compose pull db

# Fix script permissions if needed
fix-permissions:
	@echo "Fixing Docker script permissions..."
	chmod +x docker/*.sh
	@echo "Script permissions fixed."