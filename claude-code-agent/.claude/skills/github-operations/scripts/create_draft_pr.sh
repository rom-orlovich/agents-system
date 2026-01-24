#!/bin/bash
# Create a draft pull request on GitHub
# Usage: ./create_draft_pr.sh REPO TITLE "BODY" BASE_BRANCH HEAD_BRANCH

set -e

REPO="$1"
TITLE="$2"
BODY="$3"
BASE_BRANCH="${4:-main}"
HEAD_BRANCH="${5:-$(git branch --show-current)}"

if [ -z "$REPO" ] || [ -z "$TITLE" ]; then
    echo "Error: REPO and TITLE are required" >&2
    echo "Usage: $0 REPO TITLE \"BODY\" [BASE_BRANCH] [HEAD_BRANCH]" >&2
    exit 1
fi

# Use GitHub CLI to create draft PR
gh pr create \
    --repo "$REPO" \
    --title "$TITLE" \
    --body "$BODY" \
    --base "$BASE_BRANCH" \
    --head "$HEAD_BRANCH" \
    --draft

echo "Draft PR created successfully"
