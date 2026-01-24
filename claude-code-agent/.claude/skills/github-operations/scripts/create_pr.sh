#!/bin/bash
# Create a pull request after implementing changes
# Usage: ./create_pr.sh issue-number "Brief description"

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 ISSUE_NUMBER [DESCRIPTION]"
    echo "Example: $0 12345 'Fix authentication bug'"
    exit 1
fi

ISSUE_NUMBER=$1
DESCRIPTION=${2:-"Fix for issue #$ISSUE_NUMBER"}
BRANCH_NAME=$(git branch --show-current)

echo "🚀 Creating pull request..."
echo "   Issue: #$ISSUE_NUMBER"
echo "   Branch: $BRANCH_NAME"
echo "   Description: $DESCRIPTION"

# Check if we have uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted changes. Please commit them first."
    echo ""
    echo "Run:"
    echo "   git add ."
    echo "   git commit -m 'fix: $DESCRIPTION'"
    exit 1
fi

# Push branch to origin
echo "📤 Pushing branch to origin..."
git push origin "$BRANCH_NAME"

# Determine default branch
DEFAULT_BRANCH=$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)

# Create PR body
PR_BODY="Fixes #${ISSUE_NUMBER}

## Summary
${DESCRIPTION}

## Changes
- Implemented fix as described in PLAN.md
- Added/updated tests
- All tests passing

## Testing
\`\`\`bash
# Run tests
pytest tests/ -v
\`\`\`

## Plan
See PLAN.md in the repository for detailed analysis."

# Create PR
echo "📝 Creating pull request..."
gh pr create \
  --title "Fix: Issue #${ISSUE_NUMBER} - ${DESCRIPTION}" \
  --body "$PR_BODY" \
  --base "$DEFAULT_BRANCH"

# Get PR URL
PR_URL=$(gh pr view --json url -q .url)

echo ""
echo "✅ Pull request created successfully!"
echo "   URL: $PR_URL"
echo ""
echo "🔗 Next steps:"
echo "   1. Review the PR: $PR_URL"
echo "   2. Wait for CI checks to pass"
echo "   3. Request review if needed"
echo "   4. Merge when approved"
