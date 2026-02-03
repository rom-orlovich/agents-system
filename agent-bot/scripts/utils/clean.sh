#!/bin/bash
set -e

echo "Cleaning up..."

find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" \) -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Cleaned cache directories"
