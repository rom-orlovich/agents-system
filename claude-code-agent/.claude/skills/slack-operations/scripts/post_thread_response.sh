#!/bin/bash
# Post response to a Slack thread
# Usage: ./post_thread_response.sh CHANNEL_ID THREAD_TS MESSAGE
#
# Example:
#   ./post_thread_response.sh C123456 1234567890.123456 "Analysis complete: Found 3 issues"

set -e

CHANNEL_ID="$1"
THREAD_TS="$2"
MESSAGE="$3"

if [ -z "$CHANNEL_ID" ] || [ -z "$THREAD_TS" ] || [ -z "$MESSAGE" ]; then
    echo "Error: Missing required arguments" >&2
    echo "Usage: $0 CHANNEL_ID THREAD_TS MESSAGE" >&2
    exit 1
fi

if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "Error: SLACK_BOT_TOKEN is not set" >&2
    exit 1
fi

# Build JSON payload
PAYLOAD=$(cat <<EOJSON
{
  "channel": "$CHANNEL_ID",
  "thread_ts": "$THREAD_TS",
  "text": "$MESSAGE"
}
EOJSON
)

# Send to Slack
RESPONSE=$(curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

# Check response
if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo "Message posted to thread successfully"
    exit 0
else
    ERROR=$(echo "$RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "Error posting to Slack: $ERROR" >&2
    exit 1
fi
