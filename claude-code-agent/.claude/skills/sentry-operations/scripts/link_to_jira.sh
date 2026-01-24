#!/bin/bash
# Link a Sentry issue to a Jira ticket
# Usage: ./link_to_jira.sh SENTRY_ISSUE_ID JIRA_TICKET_KEY

set -e

SENTRY_ISSUE_ID="$1"
JIRA_TICKET_KEY="$2"

if [ -z "$SENTRY_ISSUE_ID" ] || [ -z "$JIRA_TICKET_KEY" ]; then
    echo "Error: SENTRY_ISSUE_ID and JIRA_TICKET_KEY are required" >&2
    echo "Usage: $0 SENTRY_ISSUE_ID JIRA_TICKET_KEY" >&2
    exit 1
fi

# Check for required environment variables
if [ -z "$JIRA_SERVER" ] || [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
    echo "Error: Missing required Jira environment variables" >&2
    exit 1
fi

if [ -z "$SENTRY_AUTH_TOKEN" ] || [ -z "$SENTRY_ORG" ]; then
    echo "Error: Missing required Sentry environment variables" >&2
    exit 1
fi

# Get Sentry issue permalink
SENTRY_URL=$(curl -s -X GET \
    "https://sentry.io/api/0/organizations/$SENTRY_ORG/issues/$SENTRY_ISSUE_ID/" \
    -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
    | jq -r '.permalink')

# Add remote link to Jira ticket
curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Basic $(echo -n "$JIRA_EMAIL:$JIRA_API_TOKEN" | base64)" \
    "$JIRA_SERVER/rest/api/3/issue/$JIRA_TICKET_KEY/remotelink" \
    -d "{
        \"object\": {
            \"url\": \"$SENTRY_URL\",
            \"title\": \"Sentry Issue: $SENTRY_ISSUE_ID\"
        }
    }"

echo "Linked Sentry issue $SENTRY_ISSUE_ID to Jira ticket $JIRA_TICKET_KEY"
