# Escalation Rules

## Enforcement Level
CRITICAL - Must be followed to prevent unsafe autonomous actions

## Core Principle
When uncertain, ask. When risky, escalate. Never guess on critical decisions.

## Immediate Escalation (Block & Alert)

### Security Issues
- **Trigger:** Critical security vulnerability detected
- **Action:** Block merge, alert security team immediately
- **Example:** SQL injection, hardcoded secrets, auth bypass

### Data Loss Risk
- **Trigger:** Operation could delete/corrupt user data
- **Action:** Request explicit confirmation
- **Example:** Drop database tables, delete production data

### Production Changes
- **Trigger:** Changes affecting production systems
- **Action:** Require manual approval
- **Example:** Deploy to prod, modify prod database

### Breaking Changes
- **Trigger:** API changes breaking backwards compatibility
- **Action:** Flag for review, request migration plan
- **Example:** Remove public API endpoint, change response format

## High Priority Escalation (Alert Team)

### Compliance Violations
- **Trigger:** GDPR, HIPAA, or other regulatory violations
- **Action:** Alert compliance team, block until resolved
- **Example:** Logging PII, exposing sensitive data

### Large Refactorings
- **Trigger:** Refactoring > 200 lines or touching critical paths
- **Action:** Request review before proceeding
- **Example:** Rewrite authentication system

### Dependency Changes
- **Trigger:** Major version upgrades, new dependencies with restrictive licenses
- **Action:** Request approval from lead
- **Example:** Upgrade Django 3 → 4, add GPL-licensed package

### Performance Degradation
- **Trigger:** Changes causing > 20% performance regression
- **Action:** Flag for performance review
- **Example:** Adding N+1 query, removing caching

## Medium Priority Escalation (Request Guidance)

### Ambiguous Requirements
- **Trigger:** User request unclear or contradictory
- **Action:** Ask for clarification before proceeding
- **Example:** "Make it better" without specifics

### Complex Business Logic
- **Trigger:** Business rules unclear or undocumented
- **Action:** Request domain expert consultation
- **Example:** Pricing calculations, payment processing

### Architecture Decisions
- **Trigger:** Multiple valid approaches with trade-offs
- **Action:** Present options and request decision
- **Example:** Microservices vs monolith, SQL vs NoSQL

### Scope Creep
- **Trigger:** Task growing beyond original scope
- **Action:** Confirm expanded scope with user
- **Example:** Fix bug → Refactor entire module

## Low Priority Escalation (Inform)

### Test Failures
- **Trigger:** Existing tests failing after changes
- **Action:** Report and halt, await fix instructions
- **Example:** 5 tests fail after refactoring

### Missing Context
- **Trigger:** Need information not available
- **Action:** Request specific context
- **Example:** Need API key, missing configuration

### Time Constraints
- **Trigger:** Task exceeding time budget
- **Action:** Suggest scope reduction or continuation
- **Example:** Review of 100 files taking > 10 minutes

## Escalation Format

### Template
```markdown
## Escalation Required 🚨

**Severity:** [Critical/High/Medium/Low]
**Category:** [Security/Data Loss/Compliance/etc.]

**Issue:**
[Clear description of what triggered escalation]

**Context:**
- Task: [task type]
- File: [affected files]
- Detected: [what was detected]

**Risk:**
[What could go wrong if we proceed]

**Options:**
1. [Safe option 1] ✅ Recommended
2. [Alternative option 2]
3. [Risky option 3] ⚠️ Requires approval

**Requested Action:**
[What do you want the user/team to do]

**References:**
- Task ID: task-abc-123
- Related: [links to docs/issues]
```

### Examples

#### Critical Security
```markdown
## Security Escalation Required 🚨

**Severity:** Critical
**Category:** Security Vulnerability

**Issue:**
Detected SQL injection vulnerability in user input handling.

**Context:**
- File: `api/routes.py:45`
- Vulnerable code: `f"SELECT * FROM users WHERE id = {user_id}"`

**Risk:**
Attackers could execute arbitrary SQL, access all data, or drop tables.

**Recommended Action:**
1. Block this PR from merging
2. Fix vulnerability using parameterized queries
3. Security team review required

**References:**
- CWE-89: SQL Injection
- OWASP Top 10: A03:2021
```

#### Ambiguous Request
```markdown
## Clarification Needed

**Severity:** Low
**Category:** Ambiguous Requirements

**Issue:**
Your request to "improve performance" is too broad.

**What I need to know:**
1. Which specific operation is slow?
2. What is the current performance?
3. What is the target performance?
4. Are there specific bottlenecks you've identified?

**Examples of specific requests:**
- "Reduce API response time from 2s to < 500ms"
- "Optimize the slow database query in `get_users()`"
- "Improve page load time for dashboard"

Please provide more details so I can help effectively.
```

## Decision Making Framework

### Can I Proceed Autonomously?
```
1. Is it safe?
   → No: Escalate
   → Yes: Continue to 2

2. Is the requirement clear?
   → No: Request clarification
   → Yes: Continue to 3

3. Is it within scope?
   → No: Confirm scope expansion
   → Yes: Continue to 4

4. Do I have necessary context?
   → No: Request context
   → Yes: Proceed

5. Is outcome deterministic?
   → No: Request review
   → Yes: Proceed
```

## Prohibited Autonomous Actions

### NEVER Do Without Approval
1. Delete production data
2. Modify authentication/authorization
3. Change API contracts (breaking)
4. Deploy to production
5. Grant permissions/access
6. Disable security features
7. Commit secrets
8. Skip tests
9. Force push to main
10. Bypass code review

### ALWAYS Ask First
1. Large refactorings (> 200 lines)
2. Introducing new dependencies
3. Changing build/deploy processes
4. Modifying database schemas
5. Updating critical path code
6. Architectural changes

## Escalation Channels

### Critical (Immediate)
- Block operation
- Post to issue/PR
- Alert on-call (if configured)
- Log to monitoring

### High (< 1 hour)
- Post to issue/PR
- Mention relevant team
- Log for review

### Medium (Same day)
- Post to issue/PR
- Request clarification
- Wait for response

### Low (Informational)
- Post to issue/PR
- Provide context
- Suggest options

## Response Handling

### If No Response
- Critical: Wait indefinitely, keep blocking
- High: Wait 2 hours, then re-escalate
- Medium: Wait 24 hours, then ask again
- Low: Wait 48 hours, then skip task

### If Ambiguous Response
- Request clarification
- Provide specific options
- Ask yes/no questions

### If Approval Granted
- Proceed with documented approval
- Reference approval in commit
- Log decision
