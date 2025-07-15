#!/bin/bash
# Health check script for Family Wiki application
set -e

# Function to check web application health
check_web_health() {
    local url="${1:-http://localhost:5000/api/status}"
    local timeout="${2:-10}"
    
    echo "Checking web application health at $url..."
    
    if curl -sf --max-time "$timeout" "$url" >/dev/null 2>&1; then
        echo "✓ Web application is healthy"
        return 0
    else
        echo "✗ Web application health check failed"
        return 1
    fi
}

# Function to check database connectivity
check_db_health() {
    local host="${1:-db}"
    local port="${2:-5432}"
    local user="${3:-family_wiki_user}"
    local database="${4:-family_wiki}"
    
    echo "Checking database connectivity..."
    
    if pg_isready -h "$host" -p "$port" -U "$user" -d "$database" >/dev/null 2>&1; then
        echo "✓ Database is healthy"
        return 0
    else
        echo "✗ Database health check failed"
        return 1
    fi
}

# Function to check Ollama connectivity (optional)
check_ollama_health() {
    local host="${OLLAMA_HOST:-localhost}"
    local port="${OLLAMA_PORT:-11434}"
    local url="http://$host:$port/api/tags"
    
    echo "Checking Ollama connectivity at $url..."
    
    if curl -sf --max-time 5 "$url" >/dev/null 2>&1; then
        echo "✓ Ollama is accessible"
        return 0
    else
        echo "⚠ Ollama is not accessible (this is optional)"
        return 0  # Don't fail health check for optional service
    fi
}

# Main health check function
main() {
    local exit_code=0
    
    echo "========================================"
    echo "Family Wiki Health Check"
    echo "========================================"
    
    # Check database first
    if ! check_db_health; then
        exit_code=1
    fi
    
    # Check web application
    if ! check_web_health; then
        exit_code=1
    fi
    
    # Check Ollama (optional)
    check_ollama_health
    
    echo "========================================"
    if [ $exit_code -eq 0 ]; then
        echo "✓ Overall health check: PASSED"
    else
        echo "✗ Overall health check: FAILED"
    fi
    echo "========================================"
    
    exit $exit_code
}

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi