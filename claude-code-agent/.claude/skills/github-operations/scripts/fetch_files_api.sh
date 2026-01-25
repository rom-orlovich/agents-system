#!/bin/bash
# Fetch files from GitHub using API (no clone required)
# Usage: ./fetch_files_api.sh REPO FILE_PATH

set -e

REPO="$1"
FILE_PATH="$2"

if [ -z "$REPO" ] || [ -z "$FILE_PATH" ]; then
    echo "Error: REPO and FILE_PATH are required" >&2
    echo "Usage: $0 REPO FILE_PATH" >&2
    echo "Example: $0 owner/repo path/to/file.py" >&2
    exit 1
fi

# Check if GITHUB_TOKEN is set (without printing it)
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set" >&2
    exit 1
fi

# Use curl to fetch file content (token is in header, not logged)
curl -s \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/contents/$FILE_PATH" \
    | jq -r '.content' | base64 -d
