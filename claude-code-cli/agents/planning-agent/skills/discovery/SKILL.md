# Discovery Skill

## Purpose
Identify which repository contains the bug and which files are affected.

## When to Use
- New task arrives from Sentry alert
- New task arrives from Jira ticket with AI-Fix label
- Manual trigger with error description

## Available MCP Tools
- `github.search_code` - Search for code across repositories
- `github.get_file_content` - Read file contents
- `sentry.get_issue_events` - Get error stack traces

## Process

### Step 1: Parse Error Information
Extract key information from the error:
- Error message/title
- Stack trace (if available)
- File paths mentioned
- Function/method names
- Package/module names

### Step 2: Repository Identification
Use the following heuristics:
1. **Stack trace analysis**: Extract file paths and match to known repos
2. **Keyword matching**: Match error context to repo descriptions
3. **Code search**: Use `github.search_code` to find matching code

### Step 3: File Identification
For the identified repository:
1. Search for files mentioned in stack trace
2. Search for files containing error-related code
3. Identify related test files

## Output Format

```json
{
  "repository": "owner/repo-name",
  "confidence": 0.95,
  "affectedFiles": [
    "src/services/auth.ts",
    "src/services/auth.spec.ts"
  ],
  "rootCause": "Null pointer exception when user session expires",
  "reasoning": "Stack trace points to auth.ts line 45, session handling code",
  "relatedFiles": [
    "src/types/session.ts",
    "src/middleware/auth.ts"
  ]
}
```

## Example Usage

### Input
```
Error: TypeError: Cannot read property 'id' of undefined
  at getCurrentUser (src/services/auth.ts:45)
  at authMiddleware (src/middleware/auth.ts:23)
```

### Process
1. Search for "getCurrentUser" in organization repositories
2. Find auth.ts in repo "myorg/api-server"
3. Read auth.ts to understand the code
4. Identify that session object is not validated before access
5. Find related test file auth.spec.ts

### Output
```json
{
  "repository": "myorg/api-server",
  "confidence": 0.98,
  "affectedFiles": ["src/services/auth.ts", "src/services/auth.spec.ts"],
  "rootCause": "Missing null check for session object before accessing user property",
  "reasoning": "Stack trace clearly points to auth.ts:45 where session.user.id is accessed without null check",
  "relatedFiles": ["src/types/session.ts", "src/middleware/auth.ts"]
}
```
