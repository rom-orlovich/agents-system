#!/bin/bash
# Post a message to a Slack channel (optionally as a thread reply)
# Usage: ./post_message.sh CHANNEL "Message text" [THREAD_TS]

set -e

CHANNEL="$1"
MESSAGE="$2"
THREAD_TS="$3"  # Optional - if provided, posts as thread reply

if [ -z "$CHANNEL" ] || [ -z "$MESSAGE" ]; then
    echo "Error: CHANNEL and MESSAGE are required" >&2
    echo "Usage: $0 CHANNEL \"Message text\" [THREAD_TS]" >&2
    exit 1
fi

# Check for required environment variable
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "Error: SLACK_BOT_TOKEN environment variable is required" >&2
    exit 1
fi

# Build JSON payload
if [ -n "$THREAD_TS" ]; then
    PAYLOAD="{\"channel\": \"$CHANNEL\", \"text\": $(echo "$MESSAGE" | jq -Rs .), \"thread_ts\": \"$THREAD_TS\"}"
else
    PAYLOAD="{\"channel\": \"$CHANNEL\", \"text\": $(echo "$MESSAGE" | jq -Rs .)}"
fi

# Post message using Slack API
RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    "https://slack.com/api/chat.postMessage" \
    -d "$PAYLOAD")

# Check for success
if echo "$RESPONSE" | jq -e '.ok == true' > /dev/null 2>&1; then
    TS=$(echo "$RESPONSE" | jq -r '.ts')
    echo "Message posted to $CHANNEL (ts: $TS)"
else
    ERROR=$(echo "$RESPONSE" | jq -r '.error // "Unknown error"')
    echo "Error posting message: $ERROR" >&2
    exit 1
fi
