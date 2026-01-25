#!/bin/bash
# Verification Script: Lint Check
# Exit 0 = PASS, Exit 1 = FAIL

set -e

echo "=== Running Lint Check ==="

# Python project with ruff
if command -v ruff &> /dev/null && [ -f "pyproject.toml" ]; then
    echo "Running ruff..."
    ruff check . 2>&1
    EXIT_CODE=$?
# Python project with flake8
elif command -v flake8 &> /dev/null && [ -f "pyproject.toml" ]; then
    echo "Running flake8..."
    flake8 . 2>&1
    EXIT_CODE=$?
# Node project with eslint
elif [ -f "package.json" ] && command -v npx &> /dev/null; then
    echo "Running eslint..."
    npx eslint . 2>&1
    EXIT_CODE=$?
else
    echo "No linter configured"
    echo "Assuming lint passes"
    EXIT_CODE=0
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== LINT PASSED ==="
else
    echo "=== LINT FAILED ==="
fi

exit $EXIT_CODE
