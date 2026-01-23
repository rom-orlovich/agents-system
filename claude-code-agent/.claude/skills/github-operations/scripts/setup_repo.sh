#!/bin/bash
# Setup GitHub repository for work - clone or update
# Usage: ./setup_repo.sh owner/repo-name issue-number

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 REPO_NAME ISSUE_NUMBER"
    echo "Example: $0 facebook/react 12345"
    exit 1
fi

REPO_NAME=$1
ISSUE_NUMBER=$2
WORKSPACE_DIR="${WORKSPACE_DIR:-/data/workspace/repos}"
REPO_PATH="$WORKSPACE_DIR/$REPO_NAME"
BRANCH_NAME="fix/issue-${ISSUE_NUMBER}"

echo "🔧 Setting up repository: $REPO_NAME"
echo "📋 Issue: #$ISSUE_NUMBER"
echo "📂 Workspace: $WORKSPACE_DIR"

# Step 1: Check if repo exists, clone if not
if [ ! -d "$REPO_PATH" ]; then
    echo "📥 Cloning repository..."
    mkdir -p "$WORKSPACE_DIR"
    cd "$WORKSPACE_DIR"
    gh repo clone "$REPO_NAME"
    echo "✅ Repository cloned to: $REPO_PATH"
else
    echo "✅ Repository already exists at: $REPO_PATH"
fi

# Step 2: Update to latest
echo "🔄 Updating to latest changes..."
cd "$REPO_PATH"

# Determine default branch
DEFAULT_BRANCH=$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)
echo "   Default branch: $DEFAULT_BRANCH"

git checkout "$DEFAULT_BRANCH" 2>/dev/null || git checkout master 2>/dev/null || git checkout main
git pull origin "$DEFAULT_BRANCH" 2>/dev/null || git pull origin master 2>/dev/null || git pull origin main

echo "✅ Updated to latest from origin/$DEFAULT_BRANCH"

# Step 3: Create or switch to feature branch
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    echo "🌿 Switching to existing branch: $BRANCH_NAME"
    git checkout "$BRANCH_NAME"
else
    echo "🌿 Creating new branch: $BRANCH_NAME"
    git checkout -b "$BRANCH_NAME"
fi

# Step 4: Output summary
echo ""
echo "✅ Repository ready for work!"
echo ""
echo "📊 Summary:"
echo "   Repository: $REPO_NAME"
echo "   Local Path: $REPO_PATH"
echo "   Branch: $BRANCH_NAME"
echo "   Working Directory: $(pwd)"
echo ""
echo "🚀 Next steps:"
echo "   1. Analyze the issue: gh issue view $ISSUE_NUMBER"
echo "   2. Make your changes in: $REPO_PATH"
echo "   3. Run tests"
echo "   4. Commit: git commit -m 'fix: description'"
echo "   5. Push: git push origin $BRANCH_NAME"
echo "   6. Create PR: gh pr create"
