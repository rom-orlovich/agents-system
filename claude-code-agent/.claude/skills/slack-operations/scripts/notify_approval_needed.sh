#!/bin/bash
# Notify Slack that approval is needed for a Draft PR
# Includes structured summary: Background, What Was Done, Key Insights
# Button clicks post @agent approve / @agent reject to GitHub PR

set -e

# Usage: notify_approval_needed.sh <pr_url> <pr_number> <repo> <ticket_id> <title> <background> <what_done> <insights> <files_affected>

PR_URL="${1:?PR URL required}"
PR_NUMBER="${2:?PR number required}"
REPO="${3:?Repository required (owner/repo)}"
TICKET_ID="${4:-"N/A"}"
TITLE="${5:?Title required}"
BACKGROUND="${6:-"No background provided"}"
WHAT_DONE="${7:-"Plan created and ready for review"}"
INSIGHTS="${8:-"See PR for details"}"
FILES_AFFECTED="${9:-"See PLAN.md"}"

SLACK_CHANNEL="${SLACK_NOTIFICATION_CHANNEL:-#ai-agent-activity}"
SLACK_TOKEN="${SLACK_BOT_TOKEN:?SLACK_BOT_TOKEN not set}"

# Truncate long fields for Slack (max ~3000 chars per block)
truncate_text() {
  local text="$1"
  local max_len="${2:-500}"
  if [ ${#text} -gt $max_len ]; then
    echo "${text:0:$max_len}..."
  else
    echo "$text"
  fi
}

BACKGROUND_TRUNC=$(truncate_text "$BACKGROUND" 400)
WHAT_DONE_TRUNC=$(truncate_text "$WHAT_DONE" 600)
INSIGHTS_TRUNC=$(truncate_text "$INSIGHTS" 400)
FILES_TRUNC=$(truncate_text "$FILES_AFFECTED" 300)

# Build structured message with approval buttons
# Button value contains PR info for GitHub comment posting
MESSAGE=$(cat <<EOF
{
  "channel": "${SLACK_CHANNEL}",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "📋 Plan Ready for Approval",
        "emoji": true
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*${TITLE}*\n\n🎫 Ticket: \`${TICKET_ID}\`\n🔗 <${PR_URL}|View Draft PR #${PR_NUMBER}>"
      }
    },
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*📖 Background*\n${BACKGROUND_TRUNC}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*✅ What Was Done*\n${WHAT_DONE_TRUNC}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*💡 Key Insights*\n${INSIGHTS_TRUNC}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*📁 Files Affected*\n\`\`\`${FILES_TRUNC}\`\`\`"
      }
    },
    {
      "type": "divider"
    },
    {
      "type": "actions",
      "block_id": "approval_actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "📄 View PR",
            "emoji": true
          },
          "url": "${PR_URL}",
          "action_id": "view_pr"
        },
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "✅ Approve",
            "emoji": true
          },
          "style": "primary",
          "action_id": "approve_plan",
          "value": "{\"action\":\"approve\",\"repo\":\"${REPO}\",\"pr_number\":${PR_NUMBER},\"ticket_id\":\"${TICKET_ID}\"}"
        },
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "❌ Reject",
            "emoji": true
          },
          "style": "danger",
          "action_id": "reject_plan",
          "value": "{\"action\":\"reject\",\"repo\":\"${REPO}\",\"pr_number\":${PR_NUMBER},\"ticket_id\":\"${TICKET_ID}\"}"
        }
      ]
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "⚡ Clicking *Approve* posts \`@agent approve\` to GitHub PR | *Reject* posts \`@agent reject\` and requests plan revision"
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
  TS=$(echo "${RESPONSE}" | jq -r '.ts')
  CHANNEL_ID=$(echo "${RESPONSE}" | jq -r '.channel')
  echo "Approval notification sent to ${SLACK_CHANNEL}"
  echo "Message timestamp: ${TS}"
  echo "Channel ID: ${CHANNEL_ID}"

  # Output JSON for caller
  echo "{\"ok\":true,\"ts\":\"${TS}\",\"channel\":\"${CHANNEL_ID}\"}"
else
  ERROR=$(echo "${RESPONSE}" | jq -r '.error')
  echo "Failed to send notification: ${ERROR}" >&2
  echo "{\"ok\":false,\"error\":\"${ERROR}\"}"
  exit 1
fi
