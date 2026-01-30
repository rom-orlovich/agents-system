# Agent Creator - Skill for Creating Sub-Agents

## Purpose
Create well-structured sub-agents that can autonomously handle specific tasks within the agent-bot system.

## When to Use
- User requests to create a specialized agent
- Need autonomous task handling for specific domain
- Building modular agent architecture

## Inputs
- **agent_name**: string - Name of the agent (e.g., "github-pr-reviewer")
- **purpose**: string - What the agent does
- **capabilities**: list[string] - What tasks agent can perform
- **required_skills**: list[string] - Skills agent needs

## Outputs
- **agent_file**: path - Created `.claude/agents/{name}.md`
- **validation_result**: boolean - Whether agent structure is valid

## Process

### 1. Design Agent Scope
- Define agent's specific domain (GitHub PRs, Jira issues, etc.)
- List all capabilities agent should have
- Identify required skills and tools
- Ensure agent has single, clear responsibility

### 2. Create Agent File

File location: `.claude/agents/{agent-name}.md`

Template:
```markdown
# [Agent Name]

## Role
[One sentence describing agent's role]

## Capabilities
- [Capability 1 with specific action]
- [Capability 2 with specific action]
- [Capability 3 with specific action]

## When to Activate
This agent activates when:
- [Trigger condition 1]
- [Trigger condition 2]
- [Trigger condition 3]

## Required Skills
- [skill-name-1]: [Why this skill is needed]
- [skill-name-2]: [Why this skill is needed]

## Required Tools
- [tool-name-1]: [What tool is used for]
- [tool-name-2]: [What tool is used for]

## Decision Making
This agent will:
1. [Decision step 1]
2. [Decision step 2]
3. [Decision step 3]

## Success Criteria
- [Measurable criterion 1]
- [Measurable criterion 2]

## Escalation Rules
Escalate to human when:
- [Condition requiring human input]
- [Condition beyond agent capability]

## Example Tasks
\`\`\`
Input: [Example input]
Process: [How agent handles it]
Output: [Expected output]
\`\`\`
```

### 3. Validate Agent Design
- Verify single responsibility principle
- Check all capabilities are actionable
- Ensure required skills exist
- Confirm escalation rules are clear

### 4. Test Agent Specification
- Create sample tasks agent should handle
- Verify agent can complete with available skills
- Check decision-making logic is sound

## Best Practices

### Agent Design Principles
- ✅ **Single Domain**: Agent handles one specific area
- ✅ **Clear Triggers**: Obvious when agent activates
- ✅ **Autonomous**: Can complete tasks without constant guidance
- ✅ **Bounded**: Know what agent should NOT do
- ✅ **Composable**: Can work with other agents

### Do's
- ✅ Define precise activation conditions
- ✅ List all required skills explicitly
- ✅ Include success criteria
- ✅ Specify escalation rules
- ✅ Provide concrete examples

### Don'ts
- ❌ Create agents that do everything
- ❌ Overlap with existing agents
- ❌ Skip escalation rules
- ❌ Forget to list required tools
- ❌ Make agents too narrow (one-task agents)

## Example: Creating GitHub PR Review Agent

```markdown
# GitHub PR Review Agent

## Role
Autonomous reviewer for GitHub pull requests, providing code analysis and feedback.

## Capabilities
- Analyze PR diff for code quality issues
- Check for security vulnerabilities
- Verify tests are included
- Post review comments
- Add emoji reactions based on PR quality

## When to Activate
This agent activates when:
- New PR is created with `@agent review` in description
- PR is updated and labeled with `needs-review`
- Comment contains `@agent review this PR`

## Required Skills
- code-analysis: Analyze code quality and patterns
- security-scanning: Identify potential vulnerabilities
- test-verification: Check test coverage
- github-api: Interact with GitHub API via MCP

## Required Tools
- github_mcp: Post comments and reactions
- ast-parser: Parse code for analysis
- regex: Pattern matching for security checks

## Decision Making
This agent will:
1. Fetch PR diff using github_mcp
2. Parse files using ast-parser
3. Run security checks with security-scanning skill
4. Verify tests exist using test-verification skill
5. Compile feedback and post comment
6. Add reaction based on overall quality

## Success Criteria
- All files in PR analyzed
- Comment posted with specific feedback
- Reaction added (👍 for good, 👀 for needs work)
- Security issues flagged

## Escalation Rules
Escalate to human when:
- Potential security vulnerability detected
- PR modifies authentication/authorization code
- More than 500 lines changed (too large for auto-review)
- Unable to access files in PR

## Example Tasks
\`\`\`
Input: PR #123 opened with "@agent review" in description
Process:
  1. Fetch diff for PR #123
  2. Analyze 3 changed files
  3. Find: missing type hints, no tests, good naming
  4. Post comment: "Missing type hints in api.py. No tests found. Consider adding unit tests."
  5. Add 👀 reaction (needs work)
Output: Review posted, reaction added, task logged
\`\`\`
```

## Validation Checklist
- [ ] Agent name is clear and specific
- [ ] Role defined in one sentence
- [ ] 3+ capabilities listed
- [ ] Activation triggers are specific
- [ ] All required skills listed and exist
- [ ] All required tools listed
- [ ] Decision-making process is step-by-step
- [ ] Success criteria are measurable
- [ ] Escalation rules defined
- [ ] At least one example provided
- [ ] File saved in `.claude/agents/`

## Dependencies
- Write tool
- Knowledge of available skills (from `.claude/skills/`)
- Understanding of sub-agent system

## Related
- See: `skill-creator.md` for creating skills agents use
- See: `command-creator.md` for creating commands that trigger agents
- See: https://code.claude.com/docs/en/sub-agents

## Error Handling
- **Duplicate agent**: Check `.claude/agents/` for existing agent
- **Missing skills**: Create required skills first using skill-creator
- **Too broad**: Split into multiple focused agents
- **No activation triggers**: Define at least 3 specific triggers
