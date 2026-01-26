#!/bin/bash

set -euo pipefail

PAYLOAD=$(cat)

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi

PROVIDER=$(echo "$PAYLOAD" | jq -r '.provider // .webhookEvent // empty' | head -c 20)

if echo "$PAYLOAD" | jq -e '.repository // .pull_request // .issue // .comment' > /dev/null 2>&1; then
    COMMENT_BODY=$(echo "$PAYLOAD" | jq -r '.comment.body // empty')
    PR_TITLE=$(echo "$PAYLOAD" | jq -r '.pull_request.title // empty')
    PR_BODY=$(echo "$PAYLOAD" | jq -r '.pull_request.body // empty')
    ISSUE_TITLE=$(echo "$PAYLOAD" | jq -r '.issue.title // empty')
    ISSUE_BODY=$(echo "$PAYLOAD" | jq -r '.issue.body // empty')
    
    TEXT=""
    if [ -n "$COMMENT_BODY" ]; then
        TEXT="$COMMENT_BODY"
    elif [ -n "$PR_BODY" ]; then
        TEXT="${PR_TITLE}${PR_BODY}"
    elif [ -n "$PR_TITLE" ]; then
        TEXT="$PR_TITLE"
    elif [ -n "$ISSUE_BODY" ]; then
        TEXT="${ISSUE_TITLE}${ISSUE_BODY}"
    elif [ -n "$ISSUE_TITLE" ]; then
        TEXT="$ISSUE_TITLE"
    fi
    
    if [ -z "$TEXT" ]; then
        echo "Rejected: No text content found in GitHub webhook" >&2
        exit 1
    fi
    
    if echo "$TEXT" | grep -qi "@agent"; then
        COMMAND=$(echo "$TEXT" | grep -oi "@agent[[:space:]]\+[[:alnum:]]\+" | head -1 | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
        VALID_COMMANDS="analyze plan fix review approve reject improve help"
        
        if echo "$VALID_COMMANDS" | grep -qw "$COMMAND"; then
            exit 0
        else
            echo "Rejected: @agent found but invalid command: $COMMAND" >&2
            exit 1
        fi
    else
        echo "Rejected: No @agent prefix found in GitHub webhook" >&2
        exit 1
    fi

elif echo "$PROVIDER" | grep -qi "jira"; then
    WEBHOOK_EVENT=$(echo "$PAYLOAD" | jq -r '.webhookEvent // empty')
    
    if echo "$WEBHOOK_EVENT" | grep -qi "issue_updated"; then
        CHANGELOG_ITEMS=$(echo "$PAYLOAD" | jq -r '.changelog.items[]? | select(.field == "assignee") | .toString // empty' | head -1)
        ASSIGNEE=$(echo "$PAYLOAD" | jq -r '.issue.fields.assignee.displayName // empty')
        
        if echo "$CHANGELOG_ITEMS$ASSIGNEE" | grep -qi "ai agent\|claude agent"; then
            exit 0
        fi
    fi
    
    COMMENT_BODY=$(echo "$PAYLOAD" | jq -r '.comment.body // empty')
    if [ -n "$COMMENT_BODY" ]; then
        if echo "$COMMENT_BODY" | grep -qi "@agent"; then
            COMMAND=$(echo "$COMMENT_BODY" | grep -oi "@agent[[:space:]]\+[[:alnum:]]\+" | head -1 | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
            VALID_COMMANDS="analyze plan fix review approve reject improve help"
            
            if echo "$VALID_COMMANDS" | grep -qw "$COMMAND"; then
                exit 0
            fi
        fi
    fi
    
    echo "Rejected: Jira webhook does not meet activation rules" >&2
    exit 1

elif echo "$PROVIDER" | grep -qi "slack\|event"; then
    EVENT_TEXT=$(echo "$PAYLOAD" | jq -r '.event.text // .text // empty')
    
    if [ -z "$EVENT_TEXT" ]; then
        echo "Rejected: No text found in Slack event" >&2
        exit 1
    fi
    
    if echo "$EVENT_TEXT" | grep -qi "@agent"; then
        COMMAND=$(echo "$EVENT_TEXT" | grep -oi "@agent[[:space:]]\+[[:alnum:]]\+" | head -1 | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
        VALID_COMMANDS="analyze plan fix review approve reject improve help"
        
        if echo "$VALID_COMMANDS" | grep -qw "$COMMAND"; then
            exit 0
        else
            echo "Rejected: @agent found but invalid command: $COMMAND" >&2
            exit 1
        fi
    else
        echo "Rejected: No @agent prefix found in Slack message" >&2
        exit 1
    fi

else
    echo "Rejected: Unknown webhook provider: $PROVIDER" >&2
    exit 1
fi
