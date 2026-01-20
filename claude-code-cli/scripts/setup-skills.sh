#!/bin/bash
# ==============================================================================
# Setup Claude Code Skills
# ==============================================================================
#
# Skills are instructions that Claude Code loads ONLY when needed.
# This saves tokens by not loading everything at startup!
#
# Token savings:
#   Without Skills: ~47k tokens loaded at startup
#   With Skills:    ~500 tokens at startup, load on-demand
#   Savings:        98% reduction!
#
# How Skills work:
#   1. At startup, Claude reads just the name + description
#   2. When you ask "Review PR #123", Claude finds matching skill
#   3. Only then does Claude load the full SKILL.md instructions
#
# Usage:
#   ./setup-skills.sh              # Create all skills
#   ./setup-skills.sh --list       # List created skills
#   ./setup-skills.sh --clean      # Remove all skills
#
# ==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           🎯 Claude Code Skills Setup                        ║"
    echo "║           Lazy Loading = 98% Token Savings!                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

create_skill() {
    local skill_name="$1"
    local skill_dir="${SKILLS_DIR}/${skill_name}"
    
    mkdir -p "$skill_dir"
    echo -e "${BLUE}📦 Creating: ${skill_name}${NC}"
}

# ==============================================================================
# Skill Definitions
# ==============================================================================

create_github_pr_review() {
    create_skill "github-pr-review"
    
    cat > "${SKILLS_DIR}/github-pr-review/SKILL.md" << 'EOF'
---
name: github-pr-review
description: Reviews GitHub pull requests for code quality, security issues, and best practices. Use when asked to review PRs, check code changes, or analyze commits.
allowed-tools: mcp__github, Read, Grep
---

# GitHub PR Review Skill

## Purpose
Comprehensive PR review covering:
- Security vulnerabilities (SQL injection, XSS, hardcoded secrets)
- Code quality (complexity, duplication, naming conventions)
- Best practices (error handling, testing, documentation)
- Performance issues (N+1 queries, memory leaks)

## Workflow

### 1. Fetch PR Details
```
Tool: mcp__github.pull_request_read
Parameters:
  owner: <repo_owner>
  repo: <repo_name>
  pullNumber: <pr_number>
  method: "get"
```

### 2. Get Changed Files
```
Tool: mcp__github.pull_request_read
Parameters:
  method: "get_files"
```

### 3. Get Diff
```
Tool: mcp__github.pull_request_read
Parameters:
  method: "get_diff"
```

### 4. Review Each File
For each changed file:
- Read the full file context (not just diff)
- Check for security issues
- Verify error handling
- Check for tests
- Review naming and structure

### 5. Generate Review Comment

## Security Checklist
- [ ] No hardcoded secrets/API keys
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Input validation present
- [ ] Authentication/authorization checked

## Code Quality Checklist
- [ ] Functions are small and focused
- [ ] No code duplication
- [ ] Clear naming conventions
- [ ] Proper error handling
- [ ] Comments for complex logic

## Output Format

```markdown
## PR Review: #{pr_number}

**Title:** {title}
**Author:** @{author}
**Files Changed:** {count} | **Lines:** +{added} -{removed}

### 🔴 Critical Issues
- **Security**: [Issue description with file:line]
  ```suggestion
  // Suggested fix
  ```

### 🟡 Warnings
- **Code Quality**: [Warning with context]

### 💡 Suggestions
- [Improvement ideas]

### ✅ What's Good
- [Positive feedback]

### Verdict
[✅ APPROVE | ⚠️ REQUEST CHANGES | 💬 COMMENT]

**Reason:** [Brief explanation]
```

## Examples
- "Review PR #123"
- "Check the latest PR for security issues"
- "Review PR #456 focusing on performance"
EOF
    
    echo -e "  ${GREEN}✅ github-pr-review${NC}"
}

create_sentry_error_analysis() {
    create_skill "sentry-error-analysis"
    
    cat > "${SKILLS_DIR}/sentry-error-analysis/SKILL.md" << 'EOF'
---
name: sentry-error-analysis
description: Analyzes Sentry errors, identifies patterns, finds root causes, and suggests fixes. Use when investigating production errors, crashes, or monitoring issues.
allowed-tools: mcp__sentry, Read, Grep
---

# Sentry Error Analysis Skill

## Purpose
Analyze production errors to:
- Identify error patterns and frequency
- Find root causes in code
- Suggest fixes with code examples
- Prioritize by impact

## Workflow

### 1. List Recent Issues
```
Tool: mcp__sentry.list_issues
Parameters:
  organization_slug: <org>
  project_slug: <project>
  query: "is:unresolved"
```

### 2. Get Issue Details
```
Tool: mcp__sentry.get_issue
Parameters:
  issue_id: <id>
```

### 3. Get Latest Event
```
Tool: mcp__sentry.get_event
Parameters:
  issue_id: <id>
```

### 4. Analyze Stack Trace
- Identify the originating file and line
- Use Read tool to get file contents
- Find the root cause

### 5. Generate Fix Suggestion

## Error Categories

### Critical (P0)
- Crashes affecting > 100 users
- Security vulnerabilities
- Data corruption

### High (P1)
- Errors affecting core functionality
- > 1000 events/day

### Medium (P2)
- Non-critical feature failures
- 100-1000 events/day

### Low (P3)
- Edge cases
- < 100 events/day

## Output Format

```markdown
## Sentry Error Report

**Organization:** {org}
**Project:** {project}
**Period:** Last 24 hours
**Total Unique Issues:** {count}

### 🔴 Critical (P0)

#### TypeError: Cannot read property 'x' of null
- **Events:** 1,234 | **Users:** 456
- **First seen:** 2 hours ago
- **Location:** `src/auth/login.js:123`

**Stack Trace:**
```
TypeError: Cannot read property 'email' of null
    at getUser (src/auth/login.js:123)
    at handleLogin (src/auth/login.js:45)
```

**Root Cause:** 
The `user` object is null when session expires mid-request.

**Suggested Fix:**
```javascript
// Before (line 123)
const email = user.email;

// After
const email = user?.email ?? null;
if (!email) {
  throw new SessionExpiredError();
}
```

### 🟡 High (P1)
...

### Action Items
1. [ ] **P0**: Fix null check in login.js - @assignee
2. [ ] **P1**: Add error boundary - @assignee
```

## Examples
- "Show Sentry errors from production"
- "What's causing the spike in errors?"
- "Analyze the TypeError in the checkout flow"
- "Show errors from the last hour"
EOF
    
    echo -e "  ${GREEN}✅ sentry-error-analysis${NC}"
}

create_jira_ticket_workflow() {
    create_skill "jira-ticket-workflow"
    
    cat > "${SKILLS_DIR}/jira-ticket-workflow/SKILL.md" << 'EOF'
---
name: jira-ticket-workflow
description: Manages Jira tickets - creates, updates, searches, and tracks progress. Use when working with Jira, managing sprints, or tracking bugs.
allowed-tools: mcp__atlassian, Read, Write
---

# Jira Ticket Workflow Skill

## Purpose
Full Jira ticket lifecycle management:
- Search and filter tickets
- Create tickets from errors or requirements
- Update tickets with progress
- Link PRs and commits
- Transition ticket status

## Workflow

### 1. Search Tickets
```
Tool: mcp__atlassian.search_issues
Parameters:
  jql: "project = PROJ AND status = 'In Progress'"
  maxResults: 20
```

### 2. Get Ticket Details
```
Tool: mcp__atlassian.get_issue
Parameters:
  issue_key: "PROJ-123"
```

### 3. Create Ticket
```
Tool: mcp__atlassian.create_issue
Parameters:
  project_key: "PROJ"
  summary: "Bug: [clear description]"
  description: "[Detailed description with steps to reproduce]"
  issue_type: "Bug"
  priority: "High"
  labels: ["bug", "production"]
```

### 4. Update Ticket
```
Tool: mcp__atlassian.add_comment
Parameters:
  issue_key: "PROJ-123"
  body: "PR created: https://github.com/..."
```

### 5. Transition Status
```
Tool: mcp__atlassian.transition_issue
Parameters:
  issue_key: "PROJ-123"
  transition_name: "In Review"
```

## JQL Query Examples

| Need | JQL |
|------|-----|
| My open bugs | `assignee = currentUser() AND type = Bug AND status != Done` |
| Sprint bugs | `sprint in openSprints() AND type = Bug` |
| High priority | `priority in (Highest, High) AND status != Done` |
| Recently updated | `updated >= -1d ORDER BY updated DESC` |
| Unassigned | `assignee is EMPTY AND status = Open` |

## Ticket Templates

### Bug Report
```markdown
## Description
[What is happening]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Browser: Chrome 120
- OS: macOS 14
- User role: Admin

## Additional Context
- Sentry issue: [link]
- Affected users: ~100
```

### Feature Request
```markdown
## Summary
[Brief description]

## User Story
As a [role], I want [feature] so that [benefit].

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Technical Notes
[Implementation hints]
```

## Output Format

### Search Results
```markdown
## Jira Search Results

**Query:** `{jql}`
**Found:** {count} issues

| Key | Type | Priority | Summary | Assignee | Status |
|-----|------|----------|---------|----------|--------|
| PROJ-123 | Bug | High | Login fails | @user | In Progress |
| PROJ-124 | Task | Medium | Add tests | - | Open |
```

### New Ticket
```markdown
## ✅ Created Jira Ticket

**Key:** PROJ-125
**Type:** Bug
**Priority:** High
**Summary:** [title]
**Assignee:** @user

**Link:** https://company.atlassian.net/browse/PROJ-125

Next steps:
1. Review the ticket
2. Add any missing details
3. Start work when ready
```

## Examples
- "Find all P0 bugs assigned to me"
- "Create a ticket for the Sentry error we found"
- "Update PROJ-123 with the PR link"
- "Show sprint tickets"
- "What's blocked?"
EOF
    
    echo -e "  ${GREEN}✅ jira-ticket-workflow${NC}"
}

create_ci_monitor() {
    create_skill "ci-monitor"
    
    cat > "${SKILLS_DIR}/ci-monitor/SKILL.md" << 'EOF'
---
name: ci-monitor
description: Monitors CI/CD pipelines, checks build status, analyzes failures, and suggests fixes. Use when checking CI status, investigating build failures, or managing workflows.
allowed-tools: mcp__github, Read
---

# CI Monitor Skill

## Purpose
Monitor and diagnose CI/CD pipelines:
- Check workflow status
- Get failure logs
- Analyze errors
- Suggest fixes
- Re-run failed jobs

## Available GitHub MCP Tools for CI

| Tool | Purpose |
|------|---------|
| `list_workflow_runs` | List runs for a workflow |
| `get_workflow_run` | Get specific run details |
| `get_job_logs` | Get logs from jobs |
| `list_workflow_jobs` | List jobs in a run |
| `rerun_failed_jobs` | Retry failed jobs |
| `rerun_workflow_run` | Retry entire workflow |

## Workflow

### 1. Check PR Status
```
Tool: mcp__github.pull_request_read
Parameters:
  owner: <owner>
  repo: <repo>
  pullNumber: <pr>
  method: "get_status"
```

Returns check status for all CI jobs.

### 2. List Workflow Runs
```
Tool: mcp__github.list_workflow_runs
Parameters:
  owner: <owner>
  repo: <repo>
  workflow_id: "ci.yml"
  branch: "feature/my-branch"
  status: "failure"
```

### 3. Get Failed Job Logs
```
Tool: mcp__github.get_job_logs
Parameters:
  owner: <owner>
  repo: <repo>
  run_id: <run_id>
  failed_only: true
  return_content: true
  tail_lines: 100
```

### 4. Analyze Failure
Common failure patterns:
- **Test failures**: Look for FAIL or Error in output
- **Build errors**: Look for compilation errors
- **Lint errors**: Look for linting warnings/errors
- **Timeout**: Check if job hit time limit

### 5. Suggest Fix

### 6. Re-run if Needed
```
Tool: mcp__github.rerun_failed_jobs
Parameters:
  owner: <owner>
  repo: <repo>
  run_id: <run_id>
```

## Common CI Failures

### Test Failures
```
FAIL src/auth.test.js
  ● should handle expired session
    Expected: null
    Received: undefined
```
**Fix:** Check the assertion, likely a code regression.

### Build Errors
```
error TS2345: Argument of type 'string' is not assignable
```
**Fix:** Type mismatch, check recent changes.

### Dependency Issues
```
npm ERR! peer dep missing
```
**Fix:** Run `npm install` or update lockfile.

### Timeout
```
The job running on runner ... has exceeded the maximum execution time
```
**Fix:** Optimize tests or increase timeout.

## Output Format

```markdown
## CI Status: PR #{pr_number}

**Branch:** {branch}
**Last Run:** {timestamp}
**Overall:** ❌ FAILED / ✅ PASSED / ⏳ RUNNING

### Checks

| Check | Status | Duration | Details |
|-------|--------|----------|---------|
| Build | ✅ Pass | 2m 15s | - |
| Test | ❌ Fail | 4m 32s | 2 failures |
| Lint | ✅ Pass | 45s | - |
| Deploy | ⏭️ Skip | - | Blocked by Test |

### ❌ Failed: Test

**Run ID:** 12345678
**Job:** test-unit

**Error:**
```
FAIL src/auth.test.js
  ● AuthService › should handle expired session
    
    expect(received).toBe(expected)
    
    Expected: null
    Received: undefined

      45 |     const user = await authService.getCurrentUser();
      46 |     expect(user).toBe(null);
         |                  ^
```

**Analysis:**
The `getCurrentUser` function returns `undefined` instead of `null` when the session is expired.

**Suggested Fix:**
```typescript
// src/auth/service.ts line 123
async getCurrentUser(): Promise<User | null> {
  const session = await this.getSession();
  if (!session || session.isExpired) {
-   return;  // Returns undefined
+   return null;  // Explicitly return null
  }
  return session.user;
}
```

### Next Steps
1. Apply the fix above
2. Run `npm test` locally to verify
3. Push - CI will re-run automatically

Or re-run CI:
`@agent retry-ci`
```

## Examples
- "Check CI status for PR #123"
- "Why did the build fail?"
- "Show the test failures"
- "Re-run CI"
- "What's failing in main branch?"
EOF
    
    echo -e "  ${GREEN}✅ ci-monitor${NC}"
}

create_pr_workflow() {
    create_skill "pr-workflow"
    
    cat > "${SKILLS_DIR}/pr-workflow/SKILL.md" << 'EOF'
---
name: pr-workflow
description: Complete PR workflow - runs tests locally FIRST, then creates PR. Use for any code change that needs a pull request. Enforces TDD and local testing before push.
allowed-tools: mcp__github, Read, Write, Bash
---

# PR Workflow Skill

## Core Principle: LOCAL TESTS FIRST!

```
❌ BAD:  Make changes → Push → Wait for CI → Fix → Repeat (slow, expensive)
✅ GOOD: Make changes → Run tests locally → Push → CI validates (fast, cheap)
```

## Workflow Steps

### Step 1: Verify Repository Setup
```bash
# Check we're in a git repository
git status

# Check current branch
git branch --show-current

# If on main/master, create feature branch
BRANCH="fix/$(echo $ISSUE_KEY | tr '[:upper:]' '[:lower:]')-$(date +%Y%m%d)"
git checkout -b $BRANCH
```

### Step 2: Make Code Changes
Implement changes according to the plan:
1. Read the approved plan (PLAN.md or task description)
2. Implement each change step by step
3. Stage changes as you go

### Step 3: RUN LOCAL TESTS ⚠️ CRITICAL

**BEFORE pushing, you MUST run tests locally!**

#### Detect Framework
```bash
# Check for package.json → npm
# Check for requirements.txt/pyproject.toml → pytest
# Check for go.mod → go test
```

#### Node.js Projects
```bash
# Install dependencies (if needed)
npm ci

# Run tests
npm test

# Run linter
npm run lint

# Run build
npm run build

# Run type check (if TypeScript)
npm run typecheck
```

#### Python Projects
```bash
# Install dependencies
uv pip install .

# Run tests
pytest -v

# Run linter
flake8 src/ tests/

# Run type check
mypy src/

# Run formatter check
black --check .
```

### Completion Criteria for Local Tests

✅ All tests pass (exit code 0)
✅ No linting errors (or only warnings)
✅ Build succeeds
✅ No type errors

**IF TESTS FAIL**: Fix the issue and re-run. Do NOT proceed!

### Step 4: Commit Changes

```bash
# Stage specific files (NOT git add .)
git add src/affected-file.js tests/affected-file.test.js

# Commit with conventional message
git commit -m "fix(auth): handle expired session gracefully

- Add null check for user object
- Return explicit null instead of undefined
- Add unit test for session expiry

Fixes: PROJ-123"
```

### Step 5: Push and Create PR

```bash
# Push branch
git push -u origin $BRANCH
```

Then use GitHub MCP to create PR:
```
Tool: mcp__github.create_pull_request
Parameters:
  owner: <owner>
  repo: <repo>
  title: "fix(auth): handle expired session gracefully"
  body: |
    ## Summary
    Fixes the issue where expired sessions return undefined instead of null.
    
    ## Changes
    - Added null check in `getCurrentUser()`
    - Return explicit null for expired sessions
    - Added unit test coverage
    
    ## Testing
    - ✅ All local tests passed
    - ✅ Linter passed
    - ✅ Build succeeded
    
    ## Related
    - Fixes PROJ-123
    - Sentry issue: SENTRY-456
  head: $BRANCH
  base: main
  draft: false
```

### Step 6: Report Result

## Conventional Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `fix`: Bug fix
- `feat`: New feature
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change that neither fixes nor adds
- `test`: Adding tests
- `chore`: Maintenance

## Output Format

```markdown
## PR Created Successfully! 🎉

**PR:** #{number}
**URL:** {url}
**Branch:** {branch} → main

### Changes Made
- `src/auth/service.ts`: Fixed null handling
- `tests/auth/service.test.ts`: Added test case

### Local Test Results
| Check | Status | Details |
|-------|--------|---------|
| Tests | ✅ Pass | 42 tests, 0 failures |
| Lint | ✅ Pass | No errors |
| Build | ✅ Pass | Compiled in 3.2s |
| Types | ✅ Pass | No type errors |

### Next Steps
1. Wait for CI to complete (~5 min)
2. Request review from team
3. Address any feedback
4. Merge when approved
```

## Important Rules

1. **NEVER skip local tests**
2. **NEVER push if tests fail**
3. **ALWAYS use feature branches**
4. **ALWAYS use conventional commits**
5. **ALWAYS include test files in changes**
6. **NEVER commit sensitive data (keys, tokens)**

## Examples
- "Create a PR for the auth fix"
- "Make a pull request with the changes"
- "Push the fix and open a PR"
EOF
    
    echo -e "  ${GREEN}✅ pr-workflow${NC}"
}

# ==============================================================================
# Main
# ==============================================================================

list_skills() {
    echo -e "${GREEN}📋 Installed Skills:${NC}"
    echo ""
    
    if [[ -d "$SKILLS_DIR" ]]; then
        for skill_dir in "$SKILLS_DIR"/*/; do
            if [[ -f "${skill_dir}SKILL.md" ]]; then
                skill_name=$(basename "$skill_dir")
                # Extract description from SKILL.md
                desc=$(grep "^description:" "${skill_dir}SKILL.md" | head -1 | sed 's/description: //')
                echo -e "  ${BLUE}${skill_name}${NC}"
                echo -e "    ${desc:0:70}..."
                echo ""
            fi
        done
    else
        echo "  No skills installed"
    fi
}

clean_skills() {
    echo -e "${YELLOW}🧹 Removing all skills...${NC}"
    rm -rf "$SKILLS_DIR"
    echo -e "${GREEN}✅ Skills removed${NC}"
}

main() {
    case "${1:-}" in
        --list|-l)
            list_skills
            exit 0
            ;;
        --clean|-c)
            clean_skills
            exit 0
            ;;
    esac
    
    print_header
    echo ""
    
    # Create skills directory
    mkdir -p "$SKILLS_DIR"
    echo -e "${BLUE}Skills directory: ${SKILLS_DIR}${NC}"
    echo ""
    
    # Create all skills
    create_github_pr_review
    create_sentry_error_analysis
    create_jira_ticket_workflow
    create_ci_monitor
    create_pr_workflow
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "${GREEN}✅ All skills created!${NC}"
    echo ""
    echo "Skills are in: $SKILLS_DIR"
    echo ""
    echo "Token savings: 98%!"
    echo "  Before: ~47k tokens at startup"
    echo "  After:  ~500 tokens (names only)"
    echo ""
    echo "Test with:"
    echo "  claude"
    echo "  > What skills are available?"
    echo "  > Review PR #123"
    echo "  > Show Sentry errors"
    echo "  > Check CI status"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

main "$@"
