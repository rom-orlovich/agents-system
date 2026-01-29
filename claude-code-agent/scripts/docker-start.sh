#!/bin/bash
set -e

# Sync dependencies
uv sync

# Start uvicorn with optimized reload configuration
# Use --reload-dir to only watch specific directories, preventing .venv from being scanned
# This prevents the file watcher from getting overwhelmed by thousands of files in .venv
exec uv run uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir /app/api \
    --reload-dir /app/core \
    --reload-dir /app/shared \
    --reload-dir /app/services \
    --reload-dir /app/workers \
    --reload-dir /app \
    --reload-include '*.py' \
    --reload-exclude '.venv/**' \
    --reload-exclude '**/.venv/**' \
    --reload-exclude '**/site-packages/**' \
    --reload-exclude '**/__pycache__/**' \
    --reload-exclude '**/.git/**' \
    --reload-exclude '**/.pytest_cache/**' \
    --reload-exclude '**/.mypy_cache/**' \
    --reload-exclude '**/.ruff_cache/**' \
    --reload-exclude '**/tests/**' \
    --reload-exclude '**/scripts/**'
