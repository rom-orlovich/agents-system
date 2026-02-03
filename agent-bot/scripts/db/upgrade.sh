#!/bin/bash
set -e

echo "Applying database migrations..."
cd agent-engine-package
alembic upgrade head
echo "✅ Migrations applied"
