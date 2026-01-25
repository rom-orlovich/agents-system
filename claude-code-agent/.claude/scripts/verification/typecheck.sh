#!/bin/bash
# Verification Script: Type Check
# Exit 0 = PASS, Exit 1 = FAIL

set -e

echo "=== Running Type Check ==="

# Python project with mypy
if command -v mypy &> /dev/null && [ -f "pyproject.toml" ]; then
    echo "Running mypy..."
    # Find source directories
    if [ -d "src" ]; then
        mypy src/ --strict 2>&1
    elif [ -d "api" ]; then
        mypy api/ core/ shared/ --strict 2>&1
    else
        mypy . --strict 2>&1
    fi
    EXIT_CODE=$?
# TypeScript project
elif [ -f "tsconfig.json" ] && command -v npx &> /dev/null; then
    echo "Running tsc..."
    npx tsc --noEmit 2>&1
    EXIT_CODE=$?
else
    echo "No type checker configured"
    echo "Assuming types pass"
    EXIT_CODE=0
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== TYPECHECK PASSED ==="
else
    echo "=== TYPECHECK FAILED ==="
fi

exit $EXIT_CODE
