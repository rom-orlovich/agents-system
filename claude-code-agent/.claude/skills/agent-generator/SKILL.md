---
name: agent-generator
description: Generates new agents with proper configuration and validation
user-invocable: true
---

Generate agents programmatically following Claude Code best practices. This skill contains templates and validation procedures for creating new agents.

## Quick Process

1. Collect requirements: agent name, description, role, tools needed
2. Determine configuration:
   - Model: sonnet (default), opus (complex tasks), haiku (simple)
   - PermissionMode: default (read-only), acceptEdits (implementation)
   - Context: fork (high output), inherit (needs context)
   - Hooks: Required for dangerous operations (Bash, Write)
3. Identify required skills (if any)
4. Create `.claude/agents/{name}.md`
5. Generate frontmatter with all required fields
6. Write concise instructions (20-40 lines)
7. Reference skills for detailed procedures
8. Validate: length, frontmatter completeness, no code examples

## Agent Structure

```
.claude/agents/
└── agent-name.md     # 20-40 lines, instructions only
```

## Frontmatter Template

```yaml
---
name: agent-name
description: Single sentence when to use (< 100 chars)
tools: [Read, Write, Edit, Bash]
disallowedTools: [Write(/data/credentials/*)]
model: sonnet|opus|haiku
permissionMode: default|acceptEdits|dontAsk
context: fork|inherit
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
skills:
  - skill-name-1
  - skill-name-2
---
```

**Field Rules:**
- `name`: kebab-case, lowercase
- `description`: Single sentence, < 100 chars, action-oriented
- `model`: `sonnet` (default), `opus` (complex), `haiku` (simple)
- `permissionMode`: `default` (read-only), `acceptEdits` (implementation), `dontAsk` (dangerous)
- `context`: `fork` (high-volume output), `inherit` (needs parent context)
- `hooks`: Required for dangerous operations (Bash, Write)
- `skills`: List of skills the agent can invoke

## Agent Templates

**Read-Only Agent:**
```yaml
tools: Read, Grep, FindByName
disallowedTools: Write, Edit
permissionMode: default
context: inherit
```

**Implementation Agent:**
```yaml
tools: Read, Write, Edit, Bash
permissionMode: acceptEdits
context: inherit
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
skills: [testing]
```

**High-Volume Agent:**
```yaml
tools: Read, Bash
permissionMode: default
context: fork
skills: [testing]
```

## Content Guidelines

**Keep in Agent File (20-40 lines):**
- Role and responsibilities
- Process/workflow steps
- When to use this agent
- References to skills for detailed procedures

**Delegate to Skills:**
- Code examples
- Detailed procedures
- Tutorials and best practices
- Command references

## Validation Rules

- Agent file: 20-40 lines, instructions only
- Frontmatter: Complete (name, description, tools, model, permissionMode, context)
- Description: Single sentence, < 100 chars
- No code examples: Delegate to skills
- No tutorials: Delegate to skills
- Hooks: Configure for dangerous operations

## Output

Creates agent file with validated frontmatter and concise instructions following Claude Code best practices.
