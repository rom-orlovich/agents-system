# Advanced Subagent Features

## Foreground vs Background Execution

### Foreground (Default)

- Blocks main conversation until complete
- Permission prompts passed through to user
- Can ask clarifying questions via `AskUserQuestion`

### Background

- Runs concurrently with main conversation
- Prompts for all tool permissions upfront
- Auto-denies anything not pre-approved
- Cannot ask clarifying questions (tool call fails)
- **MCP tools not available** in background

**Trigger background execution:**

```
Run this in the background
```

Or press **Ctrl+B** to background a running task.

**Disable background tasks:**

```bash
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
```

## Resuming Subagents

Each invocation creates a **fresh instance with new context**. To continue previous work:

```
Use the code-reviewer subagent to review the authentication module
[Agent completes]

Continue that code review and now analyze the authorization logic
[Claude resumes with full context]
```

Subagent transcripts are stored at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`.

**Persistence rules:**

- Transcripts persist within their session
- Unaffected by main conversation compaction
- Cleaned up after `cleanupPeriodDays` (default: 30 days)
- Can resume after restarting Claude Code by resuming the session

## Auto-Compaction

Subagents support automatic compaction at ~95% capacity. Override with:

```bash
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50
```

## Disabling Specific Subagents

Prevent Claude from using certain subagents:

**In settings.json:**

```json
{
  "permissions": {
    "deny": ["Task(Explore)", "Task(my-custom-agent)"]
  }
}
```

**Via CLI flag:**

```bash
claude --disallowedTools "Task(Explore)"
```

## Project-Level Hooks

Configure hooks in `settings.json` that respond to subagent lifecycle events. See [hooks.md](hooks.md) for details.
