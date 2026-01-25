#!/bin/bash
# Verification Script: Run Tests
# Exit 0 = PASS, Exit 1 = FAIL

set -e

echo "=== Running Tests ==="

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "ERROR: pytest not found"
    exit 1
fi

# Run pytest with coverage
pytest tests/ -v --tb=short --cov=. --cov-report=term-missing 2>&1

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== TESTS PASSED ==="
else
    echo "=== TESTS FAILED ==="
fi

exit $EXIT_CODE
