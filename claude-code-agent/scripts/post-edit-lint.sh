#!/bin/bash
# Post-edit hook to run linting after code changes
# Used as PostToolUse hook for executor agent

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.TargetFile // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Check if it's a Python file
if [[ "$FILE_PATH" == *.py ]]; then
    echo "🔍 Running linter on $FILE_PATH..."
    
    # Run ruff if available
    if command -v ruff &> /dev/null; then
        ruff check "$FILE_PATH" --fix
    fi
    
    # Run black if available
    if command -v black &> /dev/null; then
        black "$FILE_PATH" --quiet
    fi
fi

# Check if it's a JavaScript/TypeScript file
if [[ "$FILE_PATH" == *.js ]] || [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.jsx ]] || [[ "$FILE_PATH" == *.tsx ]]; then
    echo "🔍 Running linter on $FILE_PATH..."
    
    # Run eslint if available
    if command -v eslint &> /dev/null; then
        eslint "$FILE_PATH" --fix || true
    fi
fi

exit 0
