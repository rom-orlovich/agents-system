#!/bin/bash
# Post a comment to a Jira issue
# Usage: ./post_comment.sh ISSUE_KEY "Comment text"

set -e

ISSUE_KEY="$1"
COMMENT="$2"

if [ -z "$ISSUE_KEY" ]; then
    echo "Error: ISSUE_KEY is required" >&2
    echo "Usage: $0 ISSUE_KEY \"Comment text\"" >&2
    exit 1
fi

if [ -z "$COMMENT" ]; then
    echo "Error: COMMENT is required" >&2
    echo "Usage: $0 ISSUE_KEY \"Comment text\"" >&2
    exit 1
fi

# Check for required environment variables
if [ -z "$JIRA_SERVER" ] || [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
    echo "Error: Missing required environment variables (JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN)" >&2
    exit 1
fi

# Post comment using Jira REST API
# The comment should be in ADF (Atlassian Document Format) for proper formatting
curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Basic $(echo -n "$JIRA_EMAIL:$JIRA_API_TOKEN" | base64)" \
    "$JIRA_SERVER/rest/api/3/issue/$ISSUE_KEY/comment" \
    -d "{
        \"body\": {
            \"type\": \"doc\",
            \"version\": 1,
            \"content\": [
                {
                    \"type\": \"paragraph\",
                    \"content\": [
                        {
                            \"type\": \"text\",
                            \"text\": \"$COMMENT\"
                        }
                    ]
                }
            ]
        }
    }"

echo "Comment posted to $ISSUE_KEY"
