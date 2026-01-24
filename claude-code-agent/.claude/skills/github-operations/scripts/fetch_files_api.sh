#!/bin/bash
# Fetch files from GitHub using API (no clone required)
# Usage: ./fetch_files_api.sh REPO FILE_PATH

set -e

REPO="$1"
FILE_PATH="$2"

if [ -z "$REPO" ] || [ -z "$FILE_PATH" ]; then
    echo "Error: REPO and FILE_PATH are required" >&2
    echo "Usage: $0 REPO FILE_PATH" >&2
    exit 1
fi

# Use GitHub CLI to fetch file content
gh api \
    -H "Accept: application/vnd.github+json" \
    "/repos/$REPO/contents/$FILE_PATH" \
    --jq '.content' | base64 -d

