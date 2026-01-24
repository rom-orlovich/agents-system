#!/bin/bash
# Analyze a Sentry error and create investigation report
# Usage: ./analyze_sentry_error.sh ISSUE_ID

set -e

ISSUE_ID=$1

if [ -z "$ISSUE_ID" ]; then
    echo "Usage: $0 ISSUE_ID"
    exit 1
fi

echo "📊 Analyzing Sentry error: $ISSUE_ID"

# 1. Get error details
echo "📊 Fetching error details..."
sentry-cli issues show "$ISSUE_ID" --json > /tmp/sentry_issue.json

# 2. Extract key information
ERROR_TYPE=$(jq -r '.type // "Unknown"' /tmp/sentry_issue.json)
ERROR_COUNT=$(jq -r '.count // 0' /tmp/sentry_issue.json)
FIRST_SEEN=$(jq -r '.firstSeen // "Unknown"' /tmp/sentry_issue.json)
ERROR_TITLE=$(jq -r '.title // "Unknown"' /tmp/sentry_issue.json)

echo "Error Type: $ERROR_TYPE"
echo "Occurrences: $ERROR_COUNT"
echo "First Seen: $FIRST_SEEN"

# 3. Get recent events
echo "📋 Fetching recent events..."
sentry-cli events list --issue "$ISSUE_ID" --max 5 > /tmp/sentry_events.txt

# 4. Search codebase for error location
echo "🔍 Searching codebase..."
ERROR_FILE=$(jq -r '.culprit // "Unknown"' /tmp/sentry_issue.json)
echo "Affected file: $ERROR_FILE"

# 5. Get stack trace
STACK_TRACE=$(jq -r '.entries[0].data.values[0].stacktrace // "No stack trace available"' /tmp/sentry_issue.json 2>/dev/null || echo "No stack trace available")

# 6. Create investigation report
cat > SENTRY_ANALYSIS.md << EOF
# Sentry Error Analysis: $ISSUE_ID

## Error Details
- **Title:** $ERROR_TITLE
- **Type:** $ERROR_TYPE
- **Count:** $ERROR_COUNT occurrences
- **First Seen:** $FIRST_SEEN
- **Affected File:** $ERROR_FILE
- **Sentry Link:** https://sentry.io/issues/$ISSUE_ID

## Stack Trace
\`\`\`
$STACK_TRACE
\`\`\`

## Recent Events
\`\`\`
$(cat /tmp/sentry_events.txt)
\`\`\`

## Next Steps
1. Analyze affected code in: $ERROR_FILE
2. Identify root cause from stack trace
3. Check for similar errors in the past
4. Implement fix with proper error handling
5. Add tests to prevent regression
6. Deploy and monitor in Sentry

## Investigation Notes
<!-- Add your investigation notes here -->

EOF

echo "✅ Analysis saved to SENTRY_ANALYSIS.md"
echo ""
echo "📝 Review the analysis and start investigation:"
echo "   cat SENTRY_ANALYSIS.md"
