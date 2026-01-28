#!/bin/bash
# Post a comment to a GitHub issue
# Usage: ./post_issue_comment.sh OWNER REPO ISSUE_NUMBER "Comment text"

set -e

OWNER="$1"
REPO="$2"
ISSUE_NUMBER="$3"
COMMENT="$4"

if [ -z "$OWNER" ] || [ -z "$REPO" ] || [ -z "$ISSUE_NUMBER" ] || [ -z "$COMMENT" ]; then
    echo "Error: All parameters are required" >&2
    echo "Usage: $0 OWNER REPO ISSUE_NUMBER \"Comment text\"" >&2
    exit 1
fi

# Check for required environment variable
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required" >&2
    exit 1
fi

# Post comment using GitHub REST API
curl -s -X POST \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$OWNER/$REPO/issues/$ISSUE_NUMBER/comments" \
    -d "{\"body\": $(echo "$COMMENT" | jq -Rs .)}"

echo "Comment posted to $OWNER/$REPO#$ISSUE_NUMBER"
