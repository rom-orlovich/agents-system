#!/bin/bash
# Analyze task complexity to decide between clone vs API fetch
# Usage: ./analyze_complexity.sh "task description"
# Returns: "clone" or "api"

set -e

TASK_DESCRIPTION="$1"

if [ -z "$TASK_DESCRIPTION" ]; then
    echo "api"  # Default to API for empty input
    exit 0
fi

# Convert to lowercase for easier matching
TASK_LOWER=$(echo "$TASK_DESCRIPTION" | tr '[:upper:]' '[:lower:]')

# Keywords that suggest simple API fetch is sufficient
if echo "$TASK_LOWER" | grep -qE "search|find|check|view|get|show|list|read"; then
    echo "api"
    exit 0
fi

# Keywords that suggest complex analysis requiring clone
if echo "$TASK_LOWER" | grep -qE "analyze|refactor|implement|fix|change|modify|update|multi|comprehensive|deep|complex"; then
    echo "clone"
    exit 0
fi

# Default to API for unknown patterns
echo "api"
