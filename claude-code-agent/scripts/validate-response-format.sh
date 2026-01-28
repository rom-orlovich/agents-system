#!/bin/bash

set -euo pipefail

INPUT=$(cat)
FORMAT_TYPE=$(echo "$INPUT" | head -n 1)
RESPONSE_TEXT=$(echo "$INPUT" | tail -n +2)

if [ -z "$FORMAT_TYPE" ] || [ -z "$RESPONSE_TEXT" ]; then
    echo "Error: Format type and response text are required" >&2
    echo "Usage: echo -e \"FORMAT_TYPE\\nRESPONSE_TEXT\" | $0" >&2
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi

case "$FORMAT_TYPE" in
    pr_review)
        if ! echo "$RESPONSE_TEXT" | grep -q "## PR Review"; then
            echo "Rejected: Missing '## PR Review' header" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "### Summary"; then
            echo "Rejected: Missing '### Summary' section" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "### Code Quality"; then
            echo "Rejected: Missing '### Code Quality' section" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "### Findings"; then
            echo "Rejected: Missing '### Findings' section" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "### Verdict"; then
            echo "Rejected: Missing '### Verdict' section" >&2
            exit 1
        fi
        
        VERDICT=$(echo "$RESPONSE_TEXT" | grep -A 5 "### Verdict" | grep -iE "approve|request_changes|comment" | head -1)
        if [ -z "$VERDICT" ]; then
            echo "Rejected: Verdict must be one of: approve, request_changes, comment" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "\*Reviewed by AI Agent\*"; then
            echo "Rejected: Missing footer '*Reviewed by AI Agent*'" >&2
            exit 1
        fi
        
        exit 0
        ;;
    
    issue_analysis)
        if ! echo "$RESPONSE_TEXT" | grep -q "## Analysis"; then
            echo "Rejected: Missing '## Analysis' header" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "### Findings"; then
            echo "Rejected: Missing '### Findings' section" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "### Recommendations"; then
            echo "Rejected: Missing '### Recommendations' section" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | grep -q "\*Analyzed by AI Agent\*"; then
            echo "Rejected: Missing footer '*Analyzed by AI Agent*'" >&2
            exit 1
        fi
        
        exit 0
        ;;
    
    jira)
        if ! echo "$RESPONSE_TEXT" | jq . > /dev/null 2>&1; then
            echo "Rejected: Invalid JSON format" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | jq -e '.type == "doc"' > /dev/null 2>&1; then
            echo "Rejected: Missing ADF doc type" >&2
            exit 1
        fi
        
        if ! echo "$RESPONSE_TEXT" | jq -e '.content' > /dev/null 2>&1; then
            echo "Rejected: Missing content array" >&2
            exit 1
        fi
        
        exit 0
        ;;
    
    slack)
        if [ ${#RESPONSE_TEXT} -gt 4000 ]; then
            echo "Rejected: Message exceeds 4000 character limit (${#RESPONSE_TEXT} chars)" >&2
            exit 1
        fi
        
        if [ -z "$RESPONSE_TEXT" ]; then
            echo "Rejected: Empty message" >&2
            exit 1
        fi
        
        exit 0
        ;;
    
    *)
        echo "Rejected: Unknown format type: $FORMAT_TYPE" >&2
        echo "Valid types: pr_review, issue_analysis, jira, slack" >&2
        exit 1
        ;;
esac
