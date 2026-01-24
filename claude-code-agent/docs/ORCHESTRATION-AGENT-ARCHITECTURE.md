# Agent Architecture

## Overview

The **Brain agent** coordinates all operations by delegating to specialized agents. Each agent has a specific role and set of capabilities, creating a clean separation of concerns and enabling efficient task execution.

---

## Architecture Pattern

```
User Request
     ↓
Brain Agent (.claude/agents/brain.md)
     ↓
├─→ Planning Agent (analysis, planning)
├─→ Executor Agent (implementation, TDD)
├─→ Service Integrator Agent (external services)
├─→ Self-Improvement Agent (code analysis)
├─→ Agent Creator Agent (create agents)
├─→ Skill Creator Agent (create skills)
├─→ Verifier Agent (validation, verification)
└─→ Webhook Generator Agent (webhook creation)
```

---

## Brain Agent

### **File: `.claude/agents/brain.md`**

The Brain is the main orchestrator that:
- Analyzes user requests
- Routes to appropriate specialized agents
- Manages system operations (webhooks via webhook-management skill)
- Coordinates multi-agent workflows

**Configuration:**
- **Model**: opus
- **Tools**: Read, Write, Edit, Grep, FindByName, ListDir, Bash
- **Skills**: webhook-management
- **Permission Mode**: acceptEdits

### Delegation Pattern

1. **Understand** user request
2. **Identify** required agent(s)
3. **Delegate** with clear context
4. **Monitor** progress
5. **Aggregate** results
6. **Report** back to user

### When to Delegate

- **Analysis/Planning** → `planning` agent
- **Implementation** → `executor` agent
- **Service Integration** → `service-integrator` agent
- **Code Improvement** → `self-improvement` agent
- **Create Agents** → `agent-creator` agent
- **Create Skills** → `skill-creator` agent
- **Verification** → `verifier` agent
- **Webhook Creation** → `webhook-generator` agent
- **Webhook Management** → Handle directly via webhook-management skill

---

## Specialized Agents

### Planning Agent

**File**: `.claude/agents/planning.md`

**Purpose**: Analyzes issues and creates detailed fix plans

**Capabilities:**
- Root cause analysis
- Creates PLAN.md files
- Identifies affected components
- Defines testing strategy
- Does NOT implement code

**Configuration:**
- **Model**: opus
- **Tools**: Read, Grep, FindByName, ListDir, Bash (read-only)
- **Permission Mode**: default (read-only)

### Executor Agent

**File**: `.claude/agents/executor.md`

**Purpose**: Implements code changes following strict TDD workflow

**Capabilities:**
- Test-driven development (Red → Green → Refactor)
- Resilience testing
- Acceptance validation
- Regression prevention
- E2E testing
- Creates pull requests

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Write, Edit, MultiEdit, Grep, FindByName, ListDir, Bash
- **Skills**: testing
- **Permission Mode**: acceptEdits
- **Hooks**: Bash validation, post-edit linting

**TDD Workflow:**
1. **Red**: Create failing tests
2. **Green**: Implement minimum code
3. **Refactor**: Improve code
4. **Resilience**: Add error handling
5. **Acceptance**: Validate criteria
6. **Regression**: Ensure no regressions
7. **E2E**: Validate complete workflows

### Service Integrator Agent

**File**: `.claude/agents/service-integrator.md`

**Purpose**: Integrates with external services and orchestrates cross-service workflows

**Capabilities:**
- GitHub operations (issues, PRs, releases)
- Jira operations (tickets, sprints)
- Slack operations (messages, notifications)
- Sentry operations (errors, releases)
- Cross-service workflows

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Grep, Bash
- **Skills**: github-operations, jira-operations, slack-operations, sentry-operations
- **Permission Mode**: default
- **Context**: fork

**Common Workflows:**
- Incident response (Sentry → Jira → GitHub → Slack)
- Release coordination (GitHub → Sentry → Jira → Slack)
- Bug fix workflow (Jira → GitHub → Slack)
- Status aggregation across services

### Self-Improvement Agent

**File**: `.claude/agents/self-improvement.md`

**Purpose**: Analyzes codebase for patterns and improvement opportunities

**Capabilities:**
- Pattern learning
- Code quality analysis
- Refactoring suggestions
- Technical debt tracking

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Edit, Grep, FindByName, ListDir, Bash
- **Skills**: pattern-learner, refactoring-advisor
- **Permission Mode**: acceptEdits
- **Context**: fork

### Agent Creator Agent

**File**: `.claude/agents/agent-creator.md`

**Purpose**: Creates new agents with proper configuration and validation

**Capabilities:**
- Validates agent structure
- Generates proper frontmatter
- Configures hooks and permissions
- Ensures best practices

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Write, Edit, Grep
- **Skills**: agent-generator
- **Permission Mode**: acceptEdits

### Skill Creator Agent

**File**: `.claude/agents/skill-creator.md`

**Purpose**: Creates new skills following best practices

**Capabilities:**
- Validates skill structure
- Generates proper documentation
- Organizes examples and scripts
- Ensures consistency

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Write, Edit, Grep
- **Skills**: skill-generator
- **Permission Mode**: acceptEdits

### Verifier Agent

**File**: `.claude/agents/verifier.md`

**Purpose**: Validates implementations and performs final verification

**Capabilities:**
- Final verification of implementations
- Test result validation
- Code quality checks
- Compliance verification

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Grep, FindByName, ListDir, Bash
- **Permission Mode**: default

### Webhook Generator Agent

**File**: `.claude/agents/webhook-generator.md`

**Purpose**: Creates and configures webhooks dynamically

**Capabilities:**
- Generates webhook configurations
- Creates webhook commands and triggers
- Validates webhook structure
- Tests webhook endpoints

**Configuration:**
- **Model**: sonnet
- **Tools**: Read, Write, Edit, Grep, Bash
- **Permission Mode**: acceptEdits

---

## Skills System

Skills are reusable knowledge modules that agents can invoke. Skills contain:
- **SKILL.md**: Instructions and capabilities
- **examples.md**: Code examples (optional)
- **scripts/**: Helper scripts (optional)
- **reference.md**: Detailed reference (optional)

### Available Skills

- **webhook-management**: Webhook CRUD operations
- **testing**: TDD workflow and test patterns
- **github-operations**: GitHub CLI and API operations
- **jira-operations**: Jira CLI and API operations
- **slack-operations**: Slack API operations
- **sentry-operations**: Sentry CLI operations
- **agent-generator**: Agent creation utilities
- **skill-generator**: Skill creation utilities
- **pattern-learner**: Pattern identification
- **refactoring-advisor**: Refactoring guidance
- **claude-config-updater**: Configuration management

---

## Delegation Examples

### Example 1: Bug Fix Workflow

**User**: "Fix the login bug"

**Brain → Planning Agent:**
```
Analyze the login bug and create a fix plan.
```

**Planning Agent:**
- Investigates issue
- Creates PLAN.md with root cause and strategy

**Brain → Executor Agent:**
```
Implement the fix based on PLAN.md using TDD workflow.
```

**Executor Agent:**
- Creates failing tests
- Implements fix
- Runs full test suite
- Creates PR

### Example 2: Service Integration

**User**: "Create a Jira ticket for this Sentry error"

**Brain → Service Integrator Agent:**
```
Create a Jira ticket from Sentry error XYZ.
Include error details and stack trace.
```

**Service Integrator Agent:**
- Fetches Sentry error details
- Creates Jira ticket with proper formatting
- Links Sentry error to Jira ticket

### Example 3: Webhook Creation

**User**: "Create a GitHub webhook for issue tracking"

**Brain → Webhook Generator Agent:**
```
Create a GitHub webhook for issue tracking.
Configure triggers for issue opened and commented events.
Set up command matching for @agent mentions.
```

**Webhook Generator Agent:**
- Creates webhook configuration
- Sets up triggers and commands
- Validates webhook structure
- Tests webhook endpoint

### Example 4: Multi-Agent Workflow

**User**: "Analyze this error, create a fix plan, implement it, and deploy"

**Brain coordinates:**
1. **Planning Agent**: Analyzes error, creates PLAN.md
2. **Executor Agent**: Implements fix following TDD
3. **Service Integrator Agent**: Creates GitHub PR, updates Jira
4. **Brain**: Aggregates results and reports to user

---

## Benefits of Current Architecture

### 1. Clear Separation of Concerns
- Each agent has a specific role
- Skills provide reusable capabilities
- Brain coordinates without implementing

### 2. Efficient Task Execution
- Right agent for the right task
- Parallel execution when possible
- Optimized model selection (opus for complex, sonnet for standard)

### 3. Maintainability
- Agents are independent
- Skills are modular and reusable
- Easy to add new capabilities

### 4. Testability
- Each agent can be tested independently
- Skills have isolated test suites
- Clear input/output contracts

### 5. Scalability
- Add new agents without modifying Brain
- Skills can be updated independently
- Horizontal scaling support

---

## Agent Selection Guide

| Task Type | Agent | Model | Reason |
|-----------|-------|-------|--------|
| Analysis/Planning | planning | opus | Complex reasoning |
| Implementation | executor | sonnet | Balanced performance |
| Service Integration | service-integrator | sonnet | Standard operations |
| Code Improvement | self-improvement | sonnet | Pattern analysis |
| Create Agent | agent-creator | sonnet | Structured generation |
| Create Skill | skill-creator | sonnet | Structured generation |
| Verification | verifier | sonnet | Validation tasks |
| Webhook Creation | webhook-generator | sonnet | Structured generation |
| Webhook Management | brain | opus | Direct via skill |

---

## Summary

**Current Architecture:**
- ✅ Brain analyzes and delegates
- ✅ Specialized agents for specific domains
- ✅ Skills provide reusable capabilities
- ✅ Clean separation of concerns
- ✅ Efficient model selection
- ✅ Fully testable and maintainable

**Brain delegates to specialized agents - never implements directly!**
