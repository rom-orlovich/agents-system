#!/bin/bash
# Analyze a Sentry error and format details
# Usage: ./analyze_error.sh ISSUE_ID

set -e

ISSUE_ID="$1"

if [ -z "$ISSUE_ID" ]; then
    echo "Error: ISSUE_ID is required" >&2
    echo "Usage: $0 ISSUE_ID" >&2
    exit 1
fi

# Check for required environment variables
if [ -z "$SENTRY_AUTH_TOKEN" ] || [ -z "$SENTRY_ORG" ]; then
    echo "Error: Missing required environment variables (SENTRY_AUTH_TOKEN, SENTRY_ORG)" >&2
    exit 1
fi

# Fetch error details from Sentry API
curl -s -X GET \
    "https://sentry.io/api/0/organizations/$SENTRY_ORG/issues/$ISSUE_ID/" \
    -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
    | jq -r '{
        title: .title,
        level: .level,
        status: .status,
        count: .count,
        userCount: .userCount,
        firstSeen: .firstSeen,
        lastSeen: .lastSeen,
        culprit: .culprit,
        permalink: .permalink
    }'

