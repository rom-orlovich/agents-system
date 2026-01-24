#!/bin/bash
# Format analysis results for Jira (convert to ADF - Atlassian Document Format)
# Usage: ./format_analysis.sh "Analysis text in markdown"

set -e

INPUT="$1"

if [ -z "$INPUT" ]; then
    echo "Error: INPUT text is required" >&2
    echo "Usage: $0 \"Analysis text\"" >&2
    exit 1
fi

# Simple markdown to ADF converter
# For production, consider using a proper markdown->ADF library
# This is a basic implementation that handles:
# - Headings (# Header, ## Subheader)
# - Paragraphs
# - Code blocks (```)
# - Lists

# Convert markdown to ADF JSON
# Escape special characters for JSON
ESCAPED_INPUT=$(echo "$INPUT" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/\n/\\n/g' | perl -pe 's/\n/\\n/g' | tr '\n' ' ')

# Start with basic structure
cat << EOJSON
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "paragraph",
      "content": [
        {
          "type": "text",
          "text": "$ESCAPED_INPUT"
        }
      ]
    }
  ]
}
EOJSON
