#!/bin/bash
# Utility script to wait for database to be ready
# Can be sourced by other scripts or used standalone

wait_for_database() {
    local host="${1:-db}"
    local port="${2:-5432}"
    local user="${3:-family_wiki_user}"
    local max_attempts="${4:-30}"
    local attempt=1

    echo "Waiting for PostgreSQL at ${host}:${port} (user: ${user})..."
    
    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$host" -p "$port" -U "$user" >/dev/null 2>&1; then
            echo "PostgreSQL is ready after $attempt attempts!"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting 3 seconds..."
        sleep 3
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: PostgreSQL failed to become ready after $max_attempts attempts"
    return 1
}

# If script is executed directly (not sourced), run the function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    wait_for_database "$@"
fi