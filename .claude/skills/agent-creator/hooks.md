# Conditional Tool Validation with Hooks

For fine-grained control beyond simple allow/deny lists, use `PreToolUse` hooks to validate tool usage before execution.

## Basic Hook Structure

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
```

## Validation Script Example

Create a validation script (`validate-readonly-query.sh`):

```bash
#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Block SQL write operations
if echo "$COMMAND" | grep -iE '\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b' > /dev/null; then
  echo "Blocked: Only SELECT queries allowed" >&2
  exit 2  # Exit code 2 blocks the operation
fi

exit 0
```

## Hook Exit Codes

- `0`: Allow operation to proceed
- `2`: Block operation, feed error message back to Claude
- Other exit codes: Hook failure

## Use Cases

- Enforce read-only database access
- Validate file paths before operations
- Check command safety before execution
- Restrict tool usage based on context

## Project-Level Hooks for Subagent Events

Configure hooks in `settings.json` that respond to subagent lifecycle:

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [{ "type": "command", "command": "./scripts/setup-db.sh" }]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [{ "type": "command", "command": "./scripts/cleanup.sh" }]
      }
    ]
  }
}
```

Available lifecycle events:

- `SubagentStart`: Triggered when subagent starts
- `SubagentStop`: Triggered when subagent completes
