#!/bin/bash
# Get Sentry issue details from a Jira ticket
# Usage: ./get_sentry_issue.sh ISSUE_KEY

set -e

ISSUE_KEY="$1"

if [ -z "$ISSUE_KEY" ]; then
    echo "Error: ISSUE_KEY is required" >&2
    echo "Usage: $0 ISSUE_KEY" >&2
    exit 1
fi

# Check for required environment variables
if [ -z "$JIRA_SERVER" ] || [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
    echo "Error: Missing required environment variables (JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN)" >&2
    exit 1
fi

if [ -z "$SENTRY_AUTH_TOKEN" ] || [ -z "$SENTRY_ORG" ]; then
    echo "Error: Missing required environment variables (SENTRY_AUTH_TOKEN, SENTRY_ORG)" >&2
    exit 1
fi

# Get Jira issue details
JIRA_ISSUE=$(curl -s -X GET \
    -H "Authorization: Basic $(echo -n "$JIRA_EMAIL:$JIRA_API_TOKEN" | base64)" \
    "$JIRA_SERVER/rest/api/3/issue/$ISSUE_KEY?fields=description,comment,issuelinks")

if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch Jira issue $ISSUE_KEY" >&2
    exit 1
fi

# Extract Sentry issue ID from various sources
SENTRY_ISSUE_ID=""

# 1. Check remote links (issuelinks)
SENTRY_ISSUE_ID=$(echo "$JIRA_ISSUE" | jq -r '.fields.issuelinks[]? | select(.outwardIssue == null and .inwardIssue == null) | .object.url' 2>/dev/null | grep -oP 'sentry\.io.*issues/\K[0-9]+' | head -1)

# 2. Check description for Sentry issue links
if [ -z "$SENTRY_ISSUE_ID" ]; then
    DESCRIPTION=$(echo "$JIRA_ISSUE" | jq -r '.fields.description // ""' 2>/dev/null)
    if [ -n "$DESCRIPTION" ]; then
        SENTRY_ISSUE_ID=$(echo "$DESCRIPTION" | grep -oP 'sentry\.io.*issues/\K[0-9]+' | head -1)
    fi
fi

# 3. Check comments for Sentry issue links
if [ -z "$SENTRY_ISSUE_ID" ]; then
    COMMENTS=$(echo "$JIRA_ISSUE" | jq -r '.fields.comment.comments[]?.body // ""' 2>/dev/null)
    if [ -n "$COMMENTS" ]; then
        SENTRY_ISSUE_ID=$(echo "$COMMENTS" | grep -oP 'sentry\.io.*issues/\K[0-9]+' | head -1)
    fi
fi

# 4. Check for Sentry issue ID pattern in text (e.g., "Sentry issue: 12345")
if [ -z "$SENTRY_ISSUE_ID" ]; then
    FULL_TEXT=$(echo "$JIRA_ISSUE" | jq -r '.fields.description // "" + " " + (.fields.comment.comments[]?.body // "")' 2>/dev/null)
    SENTRY_ISSUE_ID=$(echo "$FULL_TEXT" | grep -oP '(?:Sentry|sentry).*?(?:issue|Issue)[\s:]*(\d+)' | grep -oP '\d+' | head -1)
fi

if [ -z "$SENTRY_ISSUE_ID" ]; then
    echo "Error: No Sentry issue found in Jira ticket $ISSUE_KEY" >&2
    echo "Searched in: remote links, description, and comments" >&2
    exit 1
fi

# Fetch Sentry issue details
SENTRY_ISSUE=$(curl -s -X GET \
    -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    "https://sentry.io/api/0/organizations/$SENTRY_ORG/issues/$SENTRY_ISSUE_ID/")

if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch Sentry issue $SENTRY_ISSUE_ID" >&2
    exit 1
fi

# Output Sentry issue details
echo "$SENTRY_ISSUE" | jq '.'
