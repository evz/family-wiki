.PHONY: help build up down logs shell db-shell clean restart dev prod

# Default target
help:
	@echo "Family Wiki Docker Management"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev          - Start development environment (with mDNS resolution)"
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
	@echo "  make test-mdns    - Test mDNS hostname resolution (reads from .env)"
	@echo ""
	@echo "Database Management:"
	@echo "  make db-backup    - Create database backup"
	@echo "  make db-restore   - Restore database (Usage: make db-restore file=backup.sql)"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  make clean        - Clean up containers and volumes"
	@echo "  make reset        - Reset everything (destructive!)"

# Resolve mDNS hostname for Ollama host
resolve-ollama-host:
	@echo "Resolving Ollama host..."
	@if [ -f .env ]; then \
		OLLAMA_HOST=$$(grep "^OLLAMA_HOST=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "'\'''); \
		if [ -n "$$OLLAMA_HOST" ] && echo "$$OLLAMA_HOST" | grep -q "\.local$$"; then \
			echo "Found mDNS hostname in .env: $$OLLAMA_HOST"; \
			if command -v avahi-resolve >/dev/null 2>&1; then \
				echo "Attempting to resolve $$OLLAMA_HOST using mDNS..."; \
				RESOLVED_IP=$$(avahi-resolve -4 -n "$$OLLAMA_HOST" 2>/dev/null | awk '{print $$2}' | head -1); \
				if [ -n "$$RESOLVED_IP" ] && [ "$$RESOLVED_IP" != "$$OLLAMA_HOST" ]; then \
					echo "✅ Resolved $$OLLAMA_HOST to $$RESOLVED_IP"; \
					echo "OLLAMA_HOST=$$RESOLVED_IP" > .env.ollama; \
					OLLAMA_PORT=$$(grep "^OLLAMA_PORT=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "'\'''); \
					OLLAMA_MODEL=$$(grep "^OLLAMA_MODEL=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "'\'''); \
					[ -n "$$OLLAMA_PORT" ] && echo "OLLAMA_PORT=$$OLLAMA_PORT" >> .env.ollama; \
					[ -n "$$OLLAMA_MODEL" ] && echo "OLLAMA_MODEL=$$OLLAMA_MODEL" >> .env.ollama; \
				else \
					echo "⚠️  Could not resolve $$OLLAMA_HOST, using original configuration"; \
					rm -f .env.ollama; \
				fi; \
			else \
				echo "⚠️  avahi-resolve not available, using original configuration"; \
				rm -f .env.ollama; \
			fi; \
		else \
			echo "OLLAMA_HOST is not an mDNS hostname (.local), no resolution needed"; \
			rm -f .env.ollama; \
		fi; \
	else \
		echo "No .env file found, skipping mDNS resolution"; \
		rm -f .env.ollama; \
	fi

# Development environment
dev: resolve-ollama-host build-if-needed up-dev

# Smart build - only build if images don't exist or build is forced
build-if-needed:
	@echo "Checking if Docker images need building..."
	@if [ "$(FORCE_BUILD)" = "1" ] || ! docker image inspect family-wiki-web:latest >/dev/null 2>&1; then \
		echo "Building Docker images..."; \
		docker compose build; \
	else \
		echo "Docker images already exist, skipping build (use FORCE_BUILD=1 to force)"; \
	fi

build:
	@echo "Building Docker images..."
	docker compose build

up-dev:
	@echo "Starting development environment..."
	@ENV_FILES=""; \
	if [ -f .env ]; then \
		echo "Using .env configuration for local development"; \
		ENV_FILES="--env-file .env"; \
	fi; \
	if [ -f .env.ollama ]; then \
		echo "Using dynamically resolved Ollama configuration"; \
		ENV_FILES="$$ENV_FILES --env-file .env.ollama"; \
	fi; \
	if [ -n "$$ENV_FILES" ]; then \
		echo "Starting with environment files: $$ENV_FILES"; \
		docker compose $$ENV_FILES up -d; \
	else \
		echo "Using default configuration (copy .env.example to .env for offline support)"; \
		docker compose up -d; \
	fi
	@echo "Services started. Web app available at http://localhost:5000"

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
	@echo "Starting production environment with SSL..."
	@if [ ! -f .env.prod ]; then echo "Error: .env.prod file required. Copy .env.prod.example and fill in values."; exit 1; fi
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
	@echo "Production services started."
	@echo "Note: SSL certificate generation may take a few minutes on first startup."

prod-build:
	@echo "Building production Docker images..."
	docker compose -f docker-compose.prod.yml --env-file .env.prod build

prod-down:
	docker compose -f docker-compose.prod.yml --env-file .env.prod down

prod-logs:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f

# Maintenance
clean:
	@echo "Cleaning up containers..."
	docker compose down
	docker compose -f docker-compose.prod.yml down 2>/dev/null || true
	docker system prune -f
	@echo "Cleaning up dynamic configuration files..."
	rm -f .env.ollama

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

# Test mDNS hostname resolution
test-mdns:
	@echo "Testing mDNS hostname resolution..."
	@if [ -f .env ]; then \
		OLLAMA_HOST=$$(grep "^OLLAMA_HOST=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "'\'''); \
		if [ -n "$$OLLAMA_HOST" ] && echo "$$OLLAMA_HOST" | grep -q "\.local$$"; then \
			echo "Found mDNS hostname in .env: $$OLLAMA_HOST"; \
			if command -v avahi-resolve >/dev/null 2>&1; then \
				echo "✅ avahi-resolve is available"; \
				echo "Attempting to resolve $$OLLAMA_HOST..."; \
				RESOLVED_IP=$$(avahi-resolve -4 -n "$$OLLAMA_HOST" 2>/dev/null | awk '{print $$2}' | head -1); \
				if [ -n "$$RESOLVED_IP" ] && [ "$$RESOLVED_IP" != "$$OLLAMA_HOST" ]; then \
					echo "✅ SUCCESS: $$OLLAMA_HOST resolves to $$RESOLVED_IP"; \
					echo "This IP will be used as OLLAMA_HOST when running 'make dev'"; \
				else \
					echo "❌ FAILED: Could not resolve $$OLLAMA_HOST"; \
					echo "This could mean:"; \
					echo "  - The target machine is not running"; \
					echo "  - mDNS/Avahi is not working on the network"; \
					echo "  - The hostname $$OLLAMA_HOST is not advertised"; \
					echo "Development will fall back to original configuration"; \
				fi; \
			else \
				echo "❌ avahi-resolve is not installed"; \
				echo "Install with: sudo apt-get install avahi-utils (Ubuntu/Debian)"; \
				echo "Development will fall back to original configuration"; \
			fi; \
		else \
			if [ -n "$$OLLAMA_HOST" ]; then \
				echo "OLLAMA_HOST in .env is '$$OLLAMA_HOST' (not an mDNS hostname)"; \
				echo "mDNS resolution is only used for hostnames ending in .local"; \
			else \
				echo "No OLLAMA_HOST found in .env file"; \
			fi; \
			echo "No mDNS resolution needed - will use configuration as-is"; \
		fi; \
	else \
		echo "❌ No .env file found"; \
		echo "Create .env file (copy from .env.example) and set OLLAMA_HOST=your-hostname.local"; \
		echo "to enable mDNS resolution"; \
	fi

# Fix script permissions if needed
fix-permissions:
	@echo "Fixing Docker script permissions..."
	chmod +x docker/*.sh
	@echo "Script permissions fixed."