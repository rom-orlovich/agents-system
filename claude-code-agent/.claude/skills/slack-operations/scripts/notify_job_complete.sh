#!/bin/bash
# Send Slack notification when job completes
# Usage: ./notify_job_complete.sh TASK_ID STATUS [COST] [SUMMARY]

set -e

TASK_ID="$1"
STATUS="$2"
COST="${3:-0.00}"
SUMMARY="${4:-Task completed}"

if [ -z "$TASK_ID" ]; then
    echo "Error: TASK_ID is required" >&2
    echo "Usage: $0 TASK_ID STATUS [COST] [SUMMARY]" >&2
    exit 1
fi

# Check for required environment variables
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "Error: SLACK_BOT_TOKEN is not set" >&2
    exit 1
fi

CHANNEL="${SLACK_NOTIFICATION_CHANNEL:-#ai-agent-activity}"

# Set emoji based on status
if [ "$STATUS" = "completed" ]; then
    EMOJI="✅"
    STATUS_TEXT="Completed"
else
    EMOJI="❌"
    STATUS_TEXT="Failed"
fi

# Build Slack message payload
MESSAGE=$(cat <<EOJSON
{
  "channel": "$CHANNEL",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "$EMOJI *Task $STATUS_TEXT*\n*Task ID:* \`$TASK_ID\`\n*Summary:* $SUMMARY\n*Cost:* \$$COST"
      }
    }
  ]
}
EOJSON
)

# Send to Slack
curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$MESSAGE"

echo "Job completion notification sent for task $TASK_ID"
