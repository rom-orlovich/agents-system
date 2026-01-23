# GitHub Operations Examples

Complete examples for GitHub API operations and repository workflow.

## API Operations Examples

### Issues
```bash
# List open issues
gh issue list --state open --limit 20

# Create issue
gh issue create --title "Bug: Authentication fails" --body "Description" --label bug

# Close issue with comment
gh issue close 123 --comment "Fixed in PR #456"

# Search issues
gh issue list --search "is:open label:bug author:username"
```

### Pull Requests
```bash
# Create PR
gh pr create --title "Fix: Authentication bug" --body "Description" --base main

# Review PR
gh pr review 123 --approve

# Merge PR
gh pr merge 123 --squash --delete-branch

# View PR status
gh pr view 123 --json state,statusCheckRollup
```

### GitHub Actions
```bash
# List workflow runs
gh run list --workflow ci.yml --limit 10

# View run details
gh run view 123456

# Rerun failed jobs
gh run rerun 123456 --failed

# View logs
gh run view 123456 --log
```

### Releases
```bash
# Create release
gh release create v1.0.0 --title "Release 1.0.0" --notes "Release notes"

# List releases
gh release list --limit 10

# Upload assets
gh release upload v1.0.0 ./dist/app.zip
```

## Repository Workflow Examples

### Example 1: Fix GitHub Issue

Complete workflow from issue assignment to PR creation.

#### Step 1: Setup Repository
```bash
./scripts/setup_repo.sh facebook/react 12345
```

**Output:**
```
🔧 Setting up repository: facebook/react
📋 Issue: #12345
📥 Cloning repository...
✅ Repository cloned to: /data/workspace/repos/facebook/react
🔄 Updating to latest changes...
✅ Updated to latest from origin/main
🌿 Creating new branch: fix/issue-12345
✅ Repository ready for work!
```

#### Step 2: Analyze Issue
```bash
cd /data/workspace/repos/facebook/react
gh issue view 12345
```

#### Step 3: Make Changes
```bash
# Edit files
vim src/components/Button.js

# Run tests
npm test

# Verify changes
git status
```

#### Step 4: Commit Changes
```bash
./scripts/commit_changes.sh 12345 "Fix button click handler memory leak"
```

#### Step 5: Create PR
```bash
./scripts/create_pr.sh 12345 "Fix button click handler memory leak"
```

**Output:**
```
📤 Pushing branch to origin...
📝 Creating pull request...
✅ Pull request created successfully!
   URL: https://github.com/facebook/react/pull/45678
```

### Example 2: Multiple Issues in Same Repo

Working on multiple issues from the same repository.

```bash
# Setup for issue 100
./scripts/setup_repo.sh owner/repo 100

# Work on issue 100
# ... make changes ...

# Commit and create PR
./scripts/commit_changes.sh 100 "Fix authentication bug"
./scripts/create_pr.sh 100 "Fix authentication bug"

# Setup for issue 101 (same repo - just updates and creates new branch)
./scripts/setup_repo.sh owner/repo 101

# Work on issue 101
# ... make changes ...

# Commit and create PR
./scripts/commit_changes.sh 101 "Add password reset feature"
./scripts/create_pr.sh 101 "Add password reset feature"
```

### Example 3: Planning Agent → Executor Agent Workflow

Complete workflow with agent handoff.

#### Planning Agent
```bash
# 1. Setup repository
REPO_NAME="owner/repo"
ISSUE_NUMBER="123"
./scripts/setup_repo.sh "$REPO_NAME" "$ISSUE_NUMBER"

# 2. Analyze issue
cd "/data/workspace/repos/$REPO_NAME"
gh issue view "$ISSUE_NUMBER" --json title,body,labels

# 3. Search codebase
grep -r "authentication" src/

# 4. Create plan
cat > PLAN.md << 'EOF'
# Fix Plan: Issue #123

## Issue Summary
Authentication fails when session expires

## Root Cause
Session timeout not properly handled in middleware

## Fix Strategy
1. Add session validation middleware
2. Implement token refresh logic
3. Add error handling for expired sessions

## Files to Modify
- `src/middleware/auth.js` - Add session validation
- `src/utils/token.js` - Add refresh logic
- `tests/auth.test.js` - Add tests

## Testing Strategy
- Unit tests for token refresh
- Integration tests for session expiry
- Manual testing with expired tokens
EOF

# 5. Commit plan
git add PLAN.md
git commit -m "docs: add fix plan for issue #123"
git push origin "fix/issue-$ISSUE_NUMBER"
```

#### Executor Agent
```bash
# 1. Verify repository setup
cd "/data/workspace/repos/$REPO_NAME"
git checkout "fix/issue-$ISSUE_NUMBER"

# 2. Read plan
cat PLAN.md

# 3. Implement fix
# ... make code changes ...

# 4. Run tests
npm test

# 5. Commit and create PR
./scripts/commit_changes.sh 123 "Fix session expiry handling"
./scripts/create_pr.sh 123 "Fix session expiry handling"
```

### Example 4: Emergency Hotfix

Quick hotfix workflow for production issues.

```bash
# Setup with high priority
REPO="owner/production-app"
ISSUE="999"  # Critical bug

# Clone/update repo
./scripts/setup_repo.sh "$REPO" "$ISSUE"

cd "/data/workspace/repos/$REPO"

# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b "hotfix/issue-$ISSUE"

# Make minimal fix
vim src/critical-file.js

# Test thoroughly
npm test
npm run e2e-test

# Commit with clear message
git add .
git commit -m "hotfix: fix critical production bug #$ISSUE

- Fixed null pointer exception in payment processing
- Added defensive checks
- All tests passing

CRITICAL: Needs immediate deployment
Fixes #$ISSUE"

# Push and create PR with high priority
git push origin "hotfix/issue-$ISSUE"
gh pr create \
  --title "HOTFIX: Critical bug #$ISSUE" \
  --body "🚨 CRITICAL HOTFIX\n\nFixes #$ISSUE\n\nRequires immediate review and deployment." \
  --label "priority:critical,type:hotfix" \
  --base main
```

## Best Practices

### 1. Always Pull Before Starting
```bash
cd /data/workspace/repos/owner/repo
git checkout main
git pull origin main
```

### 2. Use Descriptive Branch Names
```bash
# Good
fix/issue-123-authentication-bug
feature/issue-456-password-reset
refactor/issue-789-cleanup-auth-module

# Bad
fix-bug
my-branch
test
```

### 3. Commit Often with Clear Messages
```bash
# Good commit messages
git commit -m "fix: resolve session timeout issue

- Add session validation middleware
- Implement token refresh logic
- Add error handling for expired sessions

Fixes #123"

# Bad commit messages
git commit -m "fix stuff"
git commit -m "wip"
git commit -m "updates"
```

### 4. Test Before Committing
```bash
# Run tests
npm test

# Run linter
npm run lint

# Check types
npm run type-check

# Only commit if all pass
if [ $? -eq 0 ]; then
    git commit -m "fix: your message"
fi
```

## Troubleshooting

### Repository Already Exists
```bash
# If repo exists but you want fresh clone
rm -rf /data/workspace/repos/owner/repo
./scripts/setup_repo.sh owner/repo 123
```

### Branch Already Exists
```bash
cd /data/workspace/repos/owner/repo

# Delete local branch
git branch -D fix/issue-123

# Delete remote branch
git push origin --delete fix/issue-123

# Create fresh branch
git checkout -b fix/issue-123
```

### Authentication Issues
```bash
# Check GitHub CLI auth
gh auth status

# Re-authenticate if needed
gh auth login

# Verify token has correct scopes
gh auth status --show-token
```
