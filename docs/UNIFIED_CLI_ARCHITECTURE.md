# Unified Claude Code CLI Architecture

## Overview

This document describes the unified architecture where a single Claude Code CLI instance manages all agent operations through sub-agents and skills, replacing the previous multi-agent AWS Lambda architecture.

## Architecture Principles

### Single Process, Multiple Sub-Agents
- **One Main CLI Process**: Single Claude Code CLI instance running in one terminal
- **Background Sub-Agents**: Multiple agents running as background tasks
- **Centralized Queue**: In-memory task queue managing all incoming requests
- **Skill-Based Architecture**: Each capability exposed as a skill

## Core Components

### 1. Claude Code CLI Main Process

The main process runs continuously and:
- Listens to webhook events (GitHub, Slack, Jira, Sentry)
- Manages the task queue
- Dispatches tasks to appropriate sub-agents
- Monitors sub-agent health and progress
- Provides unified logging and monitoring

### 2. Task Queue Manager

```python
class TaskQueueManager:
    """
    Centralized queue for all incoming tasks.
    Replaces DynamoDB-based task storage with in-memory queue.
    """

    def enqueue_task(task: Task) -> str:
        """Add task to queue and return task_id"""

    def dequeue_task() -> Task:
        """Get next task from queue based on priority"""

    def get_task_status(task_id: str) -> TaskStatus:
        """Query task status"""

    def update_task_status(task_id: str, status: TaskStatus):
        """Update task progress"""
```

**Features**:
- Priority-based queue (Critical > High > Normal > Low)
- Task deduplication
- Status tracking (Queued → In Progress → Completed/Failed)
- Task history (last 1000 tasks)

### 3. Sub-Agent System

Each sub-agent runs as a background task using Claude Code CLI's `Task` tool:

```python
# Example: Launching a sub-agent
task_id = launch_sub_agent(
    agent_type="planning",
    task_data=task,
    run_in_background=True
)
```

**Sub-Agent Types**:

1. **Discovery Agent** (`discovery_skill`)
   - Finds relevant repositories and files
   - Analyzes codebase structure
   - Identifies dependencies

2. **Planning Agent** (`planning_skill`)
   - Creates TDD implementation plans
   - Generates PLAN.md documents
   - Creates GitHub PRs for approval

3. **Execution Agent** (`execution_skill`)
   - Implements code based on approved plans
   - Runs tests and fixes failures
   - Commits and pushes changes

4. **CI/CD Agent** (`cicd_skill`)
   - Monitors GitHub Actions workflows
   - Auto-fixes linting and formatting issues
   - Escalates complex failures

5. **Consultation Agent** (`consultation_skill`)
   - Provides expert advice on implementation approaches
   - Reviews architectural decisions
   - Suggests optimizations

6. **Question Agent** (`question_skill`)
   - Asks clarifying questions when context is unclear
   - Validates assumptions with users
   - Gathers missing requirements

7. **Sub-Agent Manager** (`agent_manager_skill`)
   - Monitors health of all sub-agents
   - Restarts failed agents
   - Balances workload across agents
   - Collects and aggregates metrics

### 4. Skills Architecture

Skills are the building blocks of the unified CLI. Each skill:
- Has a clear, focused responsibility
- Can be invoked by the main CLI or other agents
- Returns structured results
- Logs all actions for traceability

**Skill Registry**:

```python
SKILLS = {
    'discovery': DiscoverySkill,
    'planning': PlanningSkill,
    'execution': ExecutionSkill,
    'cicd': CICDSkill,
    'consultation': ConsultationSkill,
    'question': QuestionSkill,
    'agent_manager': AgentManagerSkill,
}
```

### 5. Webhook Integration

Webhooks from external services are received and queued:

```
GitHub Webhook → TaskQueueManager → Dispatch to appropriate sub-agent
Slack Command → TaskQueueManager → Dispatch to appropriate sub-agent
Jira Event → TaskQueueManager → Dispatch to appropriate sub-agent
Sentry Alert → TaskQueueManager → Dispatch to appropriate sub-agent
```

**Webhook Server**:
- Runs as part of the main CLI process
- FastAPI-based HTTP server
- Validates webhook signatures
- Enqueues tasks with appropriate priority

## Data Flow

### Full Workflow Example: Jira Issue to Implementation

```
1. Jira Issue Created with "AI" label
   ↓
2. Webhook received by CLI webhook server
   ↓
3. Task created and enqueued in TaskQueueManager
   ↓
4. Task dispatched to Discovery Agent (background)
   ↓
5. Discovery Agent finds relevant repos/files
   ↓
6. Task transitions to Planning Agent (background)
   ↓
7. Planning Agent creates PLAN.md and GitHub PR
   ↓
8. System waits for approval (via GitHub comment or Slack)
   ↓
9. On approval, task dispatched to Execution Agent (background)
   ↓
10. Execution Agent implements code, runs tests
    ↓
11. Code pushed to GitHub, PR updated
    ↓
12. CI/CD Agent monitors GitHub Actions (background)
    ↓
13. On success, PR ready for human review
    On failure, CI/CD Agent attempts auto-fix or escalates
```

### Task State Transitions

```
QUEUED → IN_PROGRESS → AWAITING_APPROVAL → IN_PROGRESS → COMPLETED
                                           ↓
                                        FAILED → RETRY → IN_PROGRESS
```

## Implementation Strategy

### Phase 1: Core Infrastructure (TDD)
1. TaskQueueManager with tests
2. Skill base classes with tests
3. Sub-agent launcher with tests
4. Webhook server integration with tests

### Phase 2: Migrate Existing Agents
1. Convert Discovery Agent to skill
2. Convert Planning Agent to skill
3. Convert Execution Agent to skill
4. Convert CI/CD Agent to skill

### Phase 3: New Capabilities
1. Implement Consultation Skill
2. Implement Question Skill
3. Implement Agent Manager Skill

### Phase 4: Testing & Documentation
1. End-to-end integration tests
2. Performance benchmarks
3. Update all documentation
4. Migration guide from multi-agent system

## Configuration

```yaml
# unified_cli_config.yaml

cli:
  max_concurrent_agents: 5
  task_queue_size: 100
  task_history_size: 1000

webhook_server:
  host: "0.0.0.0"
  port: 8001

skills:
  discovery:
    enabled: true
    model: "claude-sonnet-4"
    timeout_seconds: 300

  planning:
    enabled: true
    model: "claude-opus-4"
    timeout_seconds: 600
    auto_approve: false

  execution:
    enabled: true
    model: "claude-opus-4"
    timeout_seconds: 1800
    max_retries: 3

  cicd:
    enabled: true
    model: "claude-sonnet-4"
    timeout_seconds: 300
    auto_fix_enabled: true

  consultation:
    enabled: true
    model: "claude-opus-4"
    timeout_seconds: 300

  question:
    enabled: true
    model: "claude-sonnet-4"
    timeout_seconds: 120

  agent_manager:
    enabled: true
    health_check_interval: 60
    restart_failed_agents: true
```

## Monitoring & Observability

### Logging
- Centralized logging to single file/stream
- Structured JSON logs for easy parsing
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Metrics
- Tasks queued/processed/failed
- Agent execution times
- Resource usage (CPU, memory)
- Queue depth over time

### Alerts
- Agent failures
- Queue backup (too many pending tasks)
- Resource exhaustion warnings

## Advantages Over Multi-Agent Architecture

1. **Simplified Operations**
   - Single process to manage
   - Easier deployment
   - Simpler monitoring

2. **Better Resource Efficiency**
   - Shared memory and resources
   - No cold start delays
   - Lower operational costs

3. **Improved Communication**
   - Direct in-memory communication between agents
   - No network overhead
   - Faster task transitions

4. **Easier Development**
   - Single codebase
   - Unified testing approach
   - Faster iteration cycles

5. **Better Debugging**
   - All logs in one place
   - Easier to trace request flows
   - Simplified error reproduction

## Migration Path

For existing deployments:

1. **Parallel Run**: Run unified CLI alongside existing AWS infrastructure
2. **Traffic Shift**: Gradually route webhook traffic to unified CLI
3. **Validation**: Verify results match between systems
4. **Cutover**: Disable AWS infrastructure once validated
5. **Cleanup**: Remove old Lambda functions and Step Functions

## Testing Strategy

### Unit Tests
- Test each skill independently
- Mock external dependencies
- Test task queue operations

### Integration Tests
- Test full workflows end-to-end
- Test webhook handling
- Test agent coordination

### Performance Tests
- Load test with multiple concurrent tasks
- Measure response times
- Test queue behavior under load

### Chaos Tests
- Simulate agent failures
- Test recovery mechanisms
- Validate retry logic

## Future Enhancements

1. **Multi-Instance Support**
   - Run multiple CLI instances for high availability
   - Distributed task queue (Redis/RabbitMQ)
   - Leader election for coordination

2. **Advanced Scheduling**
   - Time-based task scheduling
   - Resource-aware scheduling
   - Priority adjustments based on SLAs

3. **Machine Learning Integration**
   - Predict task complexity
   - Auto-tune timeouts
   - Anomaly detection

4. **Enhanced Skills**
   - Code review skill
   - Documentation generation skill
   - Performance optimization skill

## Conclusion

The unified CLI architecture provides a simpler, more efficient, and more maintainable approach to multi-agent orchestration. By leveraging Claude Code CLI's native capabilities for background tasks and skills, we can achieve better performance and easier operations compared to the distributed AWS Lambda architecture.
