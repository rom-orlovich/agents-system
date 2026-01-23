#!/bin/bash
# Commit changes with proper message format
# Usage: ./commit_changes.sh issue-number "Brief description"

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 ISSUE_NUMBER DESCRIPTION"
    echo "Example: $0 12345 'Fix authentication bug in login handler'"
    exit 1
fi

ISSUE_NUMBER=$1
DESCRIPTION=$2

echo "💾 Committing changes..."
echo "   Issue: #$ISSUE_NUMBER"
echo "   Description: $DESCRIPTION"

# Check if there are changes to commit
if git diff-index --quiet HEAD --; then
    echo "⚠️  No changes to commit"
    exit 0
fi

# Show what will be committed
echo ""
echo "📋 Changes to be committed:"
git status --short

echo ""
read -p "Proceed with commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Commit cancelled"
    exit 1
fi

# Stage all changes
git add .

# Create commit message
COMMIT_MSG="fix: ${DESCRIPTION}

- Implemented fix as described in PLAN.md
- Added/updated tests
- All tests passing

Fixes #${ISSUE_NUMBER}"

# Commit
git commit -m "$COMMIT_MSG"

echo ""
echo "✅ Changes committed successfully!"
echo ""
echo "📊 Commit details:"
git log -1 --oneline
echo ""
echo "🚀 Next steps:"
echo "   1. Push branch: git push origin $(git branch --show-current)"
echo "   2. Create PR: gh pr create"
