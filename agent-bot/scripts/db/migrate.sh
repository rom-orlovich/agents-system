#!/bin/bash
set -e

MSG="$1"

if [ -z "$MSG" ]; then
    echo "Usage: $0 <migration-message>"
    echo "Example: $0 'Add user preferences table'"
    exit 1
fi

cd agent-engine-package
alembic revision --autogenerate -m "$MSG"

echo "✅ Migration created: $MSG"
