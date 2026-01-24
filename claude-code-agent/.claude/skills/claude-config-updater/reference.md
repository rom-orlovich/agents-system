# Claude Code Best Practices Reference

This document contains key recommendations from Claude Code official documentation on settings, memory, and best practices.

## Settings

### Model Selection

**Guidelines:**
- Use `sonnet` (default) for most tasks - balanced performance and cost
- Use `opus` for complex analysis, planning, and multi-step reasoning
- Use `haiku` for simple, quick tasks that don't require deep reasoning

**When to choose each model:**
- `sonnet`: Code implementation, debugging, standard analysis
- `opus`: Complex planning, architecture decisions, multi-agent coordination
- `haiku`: Simple file operations, quick lookups, basic queries

### Tool Permissions

**Best Practices:**
- Grant only necessary tools to each agent
- Use `disallowedTools` to explicitly block dangerous operations
- Set appropriate `permissionMode`:
  - `default`: Read-only agents (planning, analysis)
  - `acceptEdits`: Implementation agents (executor)
  - `dontAsk`: Automated agents (use with caution)

**Tool Selection Guidelines:**
- Read-only agents: `Read, Grep, FindByName, ListDir`
- Implementation agents: Add `Write, Edit, MultiEdit, Bash`
- Analysis agents: `Read, Grep, CodebaseSearch` (if available)

### Context Modes

**Context Mode Selection:**
- `inherit`: Use when agent needs parent context (most sub-agents)
- `fork`: Use for high-volume output that doesn't need parent context

**When to use each:**
- `inherit`: Sub-agents that need to understand the original request
- `fork`: Agents generating large amounts of new content independently

### Hooks

**PreToolUse Hooks:**
- Validate dangerous operations (Bash commands, file writes)
- Check permissions before execution
- Log operations for audit trail

**PostToolUse Hooks:**
- Run linting after code edits
- Validate changes don't break existing functionality
- Update documentation if needed

## Memory

### Context Management

**Strategies:**
- Keep CLAUDE.md concise and focused (100-150 lines ideal)
- Reference external files rather than embedding full content
- Use skills for detailed procedures, keep main file high-level
- Structure information hierarchically

**Memory Optimization:**
- Move detailed examples to `examples.md` files
- Move scripts to `scripts/` directories
- Keep main instruction files focused on "what" and "when"
- Put "how" details in referenced files

### Information Architecture

**Best Practices:**
- Main file (CLAUDE.md): Role, capabilities, delegation patterns
- Agent files: Specific role, tools, process
- Skill files: Detailed procedures, examples, scripts
- Reference files: External documentation, standards

**Content Organization:**
- Frontmatter: Metadata (name, description, tools, model)
- Main content: Instructions, process, guidelines
- Supporting files: Examples, scripts, references

## Best Practices

### Agent Delegation Patterns

**Effective Delegation:**
- Use natural language: "Use the [agent] to [task]"
- Provide context: Include original request and relevant information
- Be specific: Clear task description and expected outcome
- Chain agents: Use results from one agent to inform next

**Delegation Examples:**
```
Use the planning subagent to analyze why users can't login
[Wait for results]
Use the executor subagent to implement the recommended fix
```

**Parallel Delegation:**
```
Use the planning subagent to analyze the auth module
Use the executor subagent to fix the database connection issue (in background)
```

### Response Style

**Guidelines:**
- Be concise and clear
- Delegate work to appropriate sub-agents
- Provide actionable information
- Show progress for long-running tasks
- Report costs and metrics when relevant
- Ask for clarification only when genuinely needed

### Agent Coordination

**Patterns:**
- Sequential: One agent completes, next uses results
- Parallel: Multiple agents work independently
- Chain: Agents build on each other's work
- Synthesis: Combine results from multiple agents

**Coordination Best Practices:**
- Pass context between agents explicitly
- Wait for critical results before proceeding
- Synthesize parallel work results
- Validate agent outputs before using

### When to Handle Tasks Directly

Handle directly when:
- User asks simple questions about system state
- User wants to see files or logs
- User asks about available agents/webhooks/skills
- Task requires quick file edits or bash commands
- No specialized sub-agent is needed

### Sub-Agent Invocation

**Best Practices:**
- Use natural language delegation
- Include necessary context
- Specify expected outcomes
- Wait for results when needed
- Chain agents appropriately

**Invocation Format:**
```
Use the [agent-name] subagent to [specific task]

Context:
- Original request: [user request]
- Previous work: [relevant context]
- Current state: [current situation]
```

## Configuration Optimization

### Model Selection Optimization

- Match model capability to task complexity
- Consider cost vs. performance trade-offs
- Use opus sparingly for complex tasks only
- Default to sonnet for most work

### Tool Permission Optimization

- Principle of least privilege
- Explicit allow/deny lists
- Validate dangerous operations
- Audit tool usage

### Context Mode Optimization

- Use inherit for context-dependent tasks
- Use fork for independent generation
- Consider memory implications
- Test context passing between agents

## Validation Checklist

When updating CLAUDE.md, verify:
- [ ] Model selection appropriate for tasks
- [ ] Tool permissions follow least privilege
- [ ] Context mode matches usage pattern
- [ ] Hooks validate dangerous operations
- [ ] Delegation patterns are clear and effective
- [ ] Response style guidelines are actionable
- [ ] Memory usage is optimized
- [ ] All sub-agents remain compatible
- [ ] Examples and references are properly linked
