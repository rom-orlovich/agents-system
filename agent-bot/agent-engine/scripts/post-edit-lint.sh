#!/bin/bash
# Post-edit hook to run linting after code changes
# Used as PostToolUse hook for executor agent in agent-bot

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.TargetFile // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Check if it's a Python file
if [[ "$FILE_PATH" == *.py ]]; then
    echo "Running linter on $FILE_PATH..."

    # Run ruff if available
    if command -v ruff &> /dev/null; then
        ruff check "$FILE_PATH" --fix --quiet 2>/dev/null || true
        ruff format "$FILE_PATH" --quiet 2>/dev/null || true
    fi
fi

# Check if it's a JavaScript/TypeScript file
if [[ "$FILE_PATH" == *.js ]] || [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.jsx ]] || [[ "$FILE_PATH" == *.tsx ]]; then
    echo "Running linter on $FILE_PATH..."

    # Run eslint if available
    if command -v eslint &> /dev/null; then
        eslint "$FILE_PATH" --fix --quiet 2>/dev/null || true
    fi

    # Run prettier if available
    if command -v prettier &> /dev/null; then
        prettier --write "$FILE_PATH" 2>/dev/null || true
    fi
fi

# Check if it's a Rust file
if [[ "$FILE_PATH" == *.rs ]]; then
    echo "Running formatter on $FILE_PATH..."

    if command -v rustfmt &> /dev/null; then
        rustfmt "$FILE_PATH" 2>/dev/null || true
    fi
fi

exit 0
