#!/bin/bash
# Post a comment to a GitHub pull request
# Usage: ./post_pr_comment.sh OWNER REPO PR_NUMBER "Comment text"

set -e

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
COMMENT="$4"

if [ -z "$OWNER" ] || [ -z "$REPO" ] || [ -z "$PR_NUMBER" ] || [ -z "$COMMENT" ]; then
    echo "Error: All parameters are required" >&2
    echo "Usage: $0 OWNER REPO PR_NUMBER \"Comment text\"" >&2
    exit 1
fi

# Check for required environment variable
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required" >&2
    exit 1
fi

# PRs use the issues API for comments
curl -s -X POST \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
    -d "{\"body\": $(echo "$COMMENT" | jq -Rs .)}"

echo "Comment posted to PR $OWNER/$REPO#$PR_NUMBER"
