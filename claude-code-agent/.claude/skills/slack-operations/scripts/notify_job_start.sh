#!/bin/bash
# Send Slack notification when job starts
# Usage: ./notify_job_start.sh TASK_ID [SOURCE] [COMMAND] [AGENT]

set -e

TASK_ID="$1"
SOURCE="${2:-unknown}"
COMMAND="${3:-unknown}"
AGENT="${4:-brain}"

if [ -z "$TASK_ID" ]; then
    echo "Error: TASK_ID is required" >&2
    echo "Usage: $0 TASK_ID [SOURCE] [COMMAND] [AGENT]" >&2
    exit 1
fi

# Check for required environment variables
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "Error: SLACK_BOT_TOKEN is not set" >&2
    exit 1
fi

CHANNEL="${SLACK_NOTIFICATION_CHANNEL:-#ai-agent-activity}"

# Build Slack message payload
MESSAGE=$(cat <<EOJSON
{
  "channel": "$CHANNEL",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🚀 *Job Started*\n*Source:* $SOURCE\n*Command:* $COMMAND\n*Task ID:* \`$TASK_ID\`\n*Agent:* $AGENT"
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

echo "Job start notification sent for task $TASK_ID"
