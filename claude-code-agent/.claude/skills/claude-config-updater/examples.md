# CLAUDE.md Update Examples

Examples of optimal CLAUDE.md configurations following Claude Code best practices.

## Example 1: Enhanced Model Selection Guidance

### Before
```markdown
## Your Capabilities

### You CAN:
- Delegate to sub-agents using natural language
- Create and edit any files in the workspace
```

### After
```markdown
## Your Capabilities

### You CAN:
- Delegate to sub-agents using natural language (e.g., "Use the planning subagent to...")
- Create and edit any files in the workspace
- Run bash commands to manage the system
- Read files and logs throughout the filesystem
- Install packages and manage dependencies
- Monitor system health and metrics
- Answer questions directly when appropriate

## Model Selection Guidelines

When delegating to sub-agents, consider their model configuration:
- **planning** (opus): Complex analysis, multi-step reasoning, architecture decisions
- **executor** (sonnet): Code implementation, debugging, standard development tasks
- **orchestration** (sonnet): System operations, webhook management, skill uploads

For direct tasks, use sonnet (default) unless complexity requires opus.
```

## Example 2: Enhanced Delegation Patterns

### Before
```markdown
## How to Delegate to Sub-Agents

Use Claude Code's native sub-agent delegation pattern:

### Planning Tasks
Use the planning subagent to analyze why users can't login
```

### After
```markdown
## How to Delegate to Sub-Agents

Use Claude Code's native sub-agent delegation pattern with proper context:

### Planning Tasks
```
Use the planning subagent to analyze why users can't login

Context:
- Original request: User reports login failures
- Error patterns: Multiple users affected, 500 errors
- Affected components: Authentication service, database
```

### Effective Delegation Principles
- **Provide context**: Include original request and relevant information
- **Be specific**: Clear task description and expected outcome
- **Chain agents**: Use results from one agent to inform next
- **Wait when needed**: Don't proceed until critical results are available
```

## Example 3: Memory Optimization

### Before
```markdown
## Available Sub-Agents

### planning
**Location:** `.claude/agents/planning.md`
**Use for:** Analysis, bug investigation, creating fix plans
**Invoke with:** "Use the planning subagent to analyze [issue]"

[Long detailed description of planning agent capabilities...]
```

### After
```markdown
## Available Sub-Agents

### planning
**Location:** `.claude/agents/planning.md`
**Use for:** Analysis, bug investigation, creating fix plans
**Invoke with:** "Use the planning subagent to analyze [issue]"
**Model:** opus (complex reasoning)
**Tools:** Read, Grep, FindByName, ListDir (read-only)

See `.claude/agents/planning.md` for complete capabilities and process.
```

**Key Improvement:** Moved detailed information to referenced file, keeping main file concise.

## Example 4: Enhanced Response Style

### Before
```markdown
## Response Style
- Be concise and clear
- Delegate work to appropriate sub-agents
```

### After
```markdown
## Response Style

- **Be concise and clear**: Get to the point quickly
- **Delegate work to appropriate sub-agents**: Don't handle complex tasks directly
- **Provide actionable information**: Give users what they need to proceed
- **Show progress for long-running tasks**: Update users on status
- **Report costs and metrics when relevant**: Track token usage and costs
- **Ask for clarification only when genuinely needed**: Don't over-question

### When to Respond Directly
- Simple questions about system state
- Requests to see files or logs
- Questions about available agents/webhooks/skills
- Quick file edits or bash commands
- Tasks that don't require specialized expertise
```

## Example 5: Complete Enhanced Structure

### Optimal CLAUDE.md Structure

```markdown
# Claude Machine Brain

## Your Role
[Clear, concise role description]

## Available Sub-Agents
[Table or list with key info, references to detailed files]

## Your Capabilities
[What you CAN and CANNOT do]

## Model Selection Guidelines
[When to use which model]

## How to Delegate to Sub-Agents
[Delegation patterns with examples]

## When to Handle Tasks Yourself
[Clear criteria for direct handling]

## Delegation Patterns
[Sequential, parallel, chain patterns]

## Response Style
[Guidelines for effective communication]

## Memory Management
[Strategies for efficient context usage]

## Current State
[System status and configuration]
```

## Key Improvements Summary

1. **Model Selection**: Added explicit guidance on when to use which model
2. **Context Passing**: Enhanced delegation examples with context
3. **Memory Optimization**: Moved details to referenced files
4. **Response Style**: More actionable and specific guidelines
5. **Structure**: Clearer organization with better separation of concerns

## Validation

After updates, verify:
- All sub-agents remain compatible
- Delegation patterns work correctly
- Memory usage is optimized
- Examples are clear and actionable
- References to external files are correct
