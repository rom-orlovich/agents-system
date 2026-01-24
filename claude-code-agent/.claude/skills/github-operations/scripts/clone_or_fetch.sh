#!/bin/bash
# Clone repository or update if already exists
# Usage: ./clone_or_fetch.sh REPO_URL [TARGET_DIR]

set -e

REPO_URL="$1"
TARGET_DIR="${2:-/data/workspace/repos}"

if [ -z "$REPO_URL" ]; then
    echo "Error: REPO_URL is required" >&2
    echo "Usage: $0 REPO_URL [TARGET_DIR]" >&2
    exit 1
fi

# Extract repo name from URL (e.g., org/repo from https://github.com/org/repo.git)
REPO_NAME=$(basename "$REPO_URL" .git)

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

REPO_PATH="$TARGET_DIR/$REPO_NAME"

if [ -d "$REPO_PATH/.git" ]; then
    echo "Repository already exists, updating..."
    cd "$REPO_PATH"
    git fetch --all
    git pull
    echo "Repository updated: $REPO_PATH"
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$REPO_PATH"
    echo "Repository cloned: $REPO_PATH"
fi

# Output the repository path for further use
echo "$REPO_PATH"
