#!/bin/bash
# Verification Script: Build Check
# Exit 0 = PASS, Exit 1 = FAIL

set -e

echo "=== Running Build Check ==="

# Check if Makefile exists
if [ -f "Makefile" ]; then
    make build 2>&1
    EXIT_CODE=$?
# Check if pyproject.toml exists (Python project)
elif [ -f "pyproject.toml" ]; then
    # Try uv build first, then pip
    if command -v uv &> /dev/null; then
        uv build 2>&1
    else
        pip install -e . 2>&1
    fi
    EXIT_CODE=$?
# Check for package.json (Node project)
elif [ -f "package.json" ]; then
    npm run build 2>&1
    EXIT_CODE=$?
else
    echo "No build system detected (Makefile, pyproject.toml, package.json)"
    echo "Assuming no build required"
    EXIT_CODE=0
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== BUILD PASSED ==="
else
    echo "=== BUILD FAILED ==="
fi

exit $EXIT_CODE
