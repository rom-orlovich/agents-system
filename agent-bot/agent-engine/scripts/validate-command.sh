#!/bin/bash
# Validation script for bash commands - blocks dangerous operations
# Used as PreToolUse hook for agents in agent-bot

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Block dangerous commands
DANGEROUS_PATTERNS=(
    'rm -rf'
    'rm -r /'
    'dd if='
    'mkfs'
    'format'
    'git push --force'
    'git push -f'
    'DROP DATABASE'
    'DROP TABLE'
    'TRUNCATE'
    '> /dev/sda'
    'chmod 777'
    'chown -R'
    ':(){:|:&};:'
    'curl | sh'
    'wget | sh'
    'curl | bash'
    'wget | bash'
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -iF "$pattern" > /dev/null; then
        echo "BLOCKED: Dangerous command detected: $pattern" >&2
        exit 2  # Exit code 2 blocks the tool call
    fi
done

# Block commands that modify credentials
if echo "$COMMAND" | grep -iE '/data/credentials|\.env|\.credentials' > /dev/null; then
    echo "BLOCKED: Cannot modify credentials or environment files" >&2
    exit 2
fi

# Block commands that could escape container
if echo "$COMMAND" | grep -iE 'docker run|docker exec|kubectl exec' > /dev/null; then
    echo "BLOCKED: Cannot run container escape commands" >&2
    exit 2
fi

# Allow the command
exit 0
