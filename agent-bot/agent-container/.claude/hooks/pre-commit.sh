#!/bin/bash
set -e

echo "Running pre-commit hooks..."

echo "1. Checking for type safety violations..."
if grep -r "Any" --include="*.py" --exclude-dir="venv" --exclude-dir=".venv" .; then
    echo "ERROR: Found 'Any' type usage. Please use explicit types."
    exit 1
fi

echo "2. Running tests..."
pytest --tb=short -q

echo "3. Checking code formatting..."
black --check .

echo "4. Running linting..."
ruff check .

echo "5. Checking for unused imports..."
autoflake --check --remove-all-unused-imports --remove-unused-variables -r .

echo "✓ All pre-commit checks passed!"
