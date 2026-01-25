#!/bin/bash
# Notify Slack that approval is needed for a Draft PR

set -e

# Usage: notify_approval_needed.sh <pr_url> <pr_title> <ticket_id> <summary>

PR_URL="${1:?PR URL required}"
PR_TITLE="${2:?PR title required}"
TICKET_ID="${3:-"N/A"}"
SUMMARY="${4:-"Plan ready for review"}"

SLACK_CHANNEL="${SLACK_NOTIFICATION_CHANNEL:-#ai-agent-activity}"
SLACK_TOKEN="${SLACK_BOT_TOKEN:?SLACK_BOT_TOKEN not set}"

# Build message with approval buttons
MESSAGE=$(cat <<EOF
{
  "channel": "${SLACK_CHANNEL}",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "📋 Plan Ready for Approval"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*${PR_TITLE}*\n\nTicket: \`${TICKET_ID}\`\n\n${SUMMARY}"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "📄 View PR"
          },
          "url": "${PR_URL}",
          "style": "primary"
        },
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "✅ Approve"
          },
          "action_id": "approve_plan_${TICKET_ID}",
          "style": "primary"
        },
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "❌ Reject"
          },
          "action_id": "reject_plan_${TICKET_ID}",
          "style": "danger"
        }
      ]
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "Reply with feedback or click a button to respond"
        }
      ]
    }
  ]
}
EOF
)

# Send to Slack
RESPONSE=$(curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer ${SLACK_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${MESSAGE}")

# Check response
if echo "${RESPONSE}" | jq -e '.ok == true' > /dev/null 2>&1; then
  echo "Approval notification sent to ${SLACK_CHANNEL}"
  echo "Message timestamp: $(echo "${RESPONSE}" | jq -r '.ts')"
else
  echo "Failed to send notification: $(echo "${RESPONSE}" | jq -r '.error')" >&2
  exit 1
fi
