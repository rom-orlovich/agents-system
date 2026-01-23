#!/bin/bash
# Validation script for read-only database queries
# Used for agents that should only read data, not modify it

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Block SQL write operations (case-insensitive)
if echo "$COMMAND" | grep -iE '\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b' > /dev/null; then
    echo "❌ BLOCKED: Only SELECT queries are allowed" >&2
    exit 2
fi

# Allow the command
exit 0
