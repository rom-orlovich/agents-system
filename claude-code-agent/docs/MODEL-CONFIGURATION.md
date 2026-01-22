# Claude Model Configuration

## Overview

You can now configure which Claude models to use for different types of tasks via environment variables. This allows you to optimize for performance and cost by using:
- **Opus 4** for complex tasks, thinking, and planning
- **Sonnet 4** for execution and faster tasks

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Opus 4 for complex tasks, thinking, and planning
CLAUDE_MODEL_PLANNING=opus-4
CLAUDE_MODEL_BRAIN=opus-4

# Sonnet 4 for execution and faster tasks
CLAUDE_MODEL_EXECUTOR=sonnet-4

# Default model if not specified (optional)
CLAUDE_DEFAULT_MODEL=sonnet-4
```

### Model Mapping

| Agent Type | Environment Variable | Default Model | Use Case |
|------------|---------------------|---------------|----------|
| **Planning** | `CLAUDE_MODEL_PLANNING` | `opus-4` | Complex analysis, thinking, planning |
| **Brain** | `CLAUDE_MODEL_BRAIN` | `opus-4` | Orchestration, decision-making |
| **Executor** | `CLAUDE_MODEL_EXECUTOR` | `sonnet-4` | Code execution, faster tasks |
| **Default** | `CLAUDE_DEFAULT_MODEL` | `sonnet-4` | Fallback for unknown agents |

---

## How It Works

### 1. **Task Creation**

When a task is created (via API, webhook, or chat), it's assigned to an agent:

```python
task = TaskDB(
    task_id="task-123",
    assigned_agent="planning",  # or "executor", "brain"
    agent_type=AgentType.PLANNING,
    input_message="Analyze this issue..."
)
```

### 2. **Model Selection**

The task worker automatically selects the appropriate model:

```python
# In workers/task_worker.py
model = settings.get_model_for_agent(task.assigned_agent)
# Returns: "opus-4" for planning, "sonnet-4" for executor
```

### 3. **CLI Execution**

The selected model is passed to Claude CLI:

```bash
claude --model opus-4 --output-format json -- "Your task..."
```

---

## Examples

### Example 1: GitHub Issue Analysis (Planning Agent)

**Task:**
```
New GitHub issue: "Bug in authentication"
→ Assigned to: planning agent
→ Model used: opus-4 (complex analysis)
```

**Why Opus 4?**
- Needs deep thinking
- Complex problem analysis
- Strategic planning required

### Example 2: Code Execution (Executor Agent)

**Task:**
```
Run tests and fix failing test
→ Assigned to: executor agent
→ Model used: sonnet-4 (fast execution)
```

**Why Sonnet 4?**
- Straightforward execution
- Faster response time
- Cost-effective for simple tasks

### Example 3: Webhook Command (Create Task)

**Webhook configuration:**
```json
{
  "trigger": "issues.opened",
  "action": "create_task",
  "agent": "planning",
  "template": "Analyze: {{issue.title}}"
}
```

**Result:**
- Task created for planning agent
- Model: opus-4 (from `CLAUDE_MODEL_PLANNING`)
- Complex analysis with deep thinking

---

## Available Models

### Claude 4 Models

| Model | Name in Config | Best For | Speed | Cost |
|-------|---------------|----------|-------|------|
| **Opus 4** | `opus-4` | Complex reasoning, thinking, planning | Slower | Higher |
| **Sonnet 4** | `sonnet-4` | Execution, coding, faster tasks | Faster | Lower |
| **Haiku 4** | `haiku-4` | Simple tasks, quick responses | Fastest | Lowest |

### Legacy Models (if needed)

| Model | Name in Config |
|-------|---------------|
| Opus 3.5 | `opus` or `claude-opus-3-5-20240229` |
| Sonnet 3.5 | `sonnet` or `claude-sonnet-3-5-20240620` |
| Haiku 3.5 | `haiku` or `claude-haiku-3-5-20240307` |

---

## Cost Optimization Strategies

### Strategy 1: Opus for Planning, Sonnet for Execution

```bash
# .env
CLAUDE_MODEL_PLANNING=opus-4      # Deep thinking
CLAUDE_MODEL_BRAIN=opus-4         # Orchestration
CLAUDE_MODEL_EXECUTOR=sonnet-4    # Fast execution
CLAUDE_DEFAULT_MODEL=sonnet-4     # Cost-effective default
```

**Benefits:**
- Complex tasks get deep reasoning (Opus)
- Simple tasks execute quickly (Sonnet)
- Optimal cost/performance balance

### Strategy 2: All Sonnet (Cost-Effective)

```bash
# .env
CLAUDE_MODEL_PLANNING=sonnet-4
CLAUDE_MODEL_BRAIN=sonnet-4
CLAUDE_MODEL_EXECUTOR=sonnet-4
CLAUDE_DEFAULT_MODEL=sonnet-4
```

**Benefits:**
- Lower costs
- Faster responses
- Good for most tasks

### Strategy 3: All Opus (Maximum Quality)

```bash
# .env
CLAUDE_MODEL_PLANNING=opus-4
CLAUDE_MODEL_BRAIN=opus-4
CLAUDE_MODEL_EXECUTOR=opus-4
CLAUDE_DEFAULT_MODEL=opus-4
```

**Benefits:**
- Best reasoning quality
- Deep analysis for all tasks
- Higher costs

---

## Customization

### Add Custom Agent Types

If you create custom agents, they'll use the default model unless you add specific configuration:

```python
# In core/config.py
claude_model_my_custom_agent: str = "opus-4"

# In get_model_for_agent method
elif agent_type_lower == "my_custom_agent":
    return self.claude_model_my_custom_agent
```

### Override Model Per Task

You can override the model for specific tasks programmatically:

```python
# When creating a task
result = await run_claude_cli(
    prompt="Your task",
    model="opus-4",  # Override default
    ...
)
```

---

## Monitoring

### Check Which Model Was Used

View logs to see model selection:

```bash
docker-compose logs -f claude-code-agent | grep selected_model_for_task
```

Output:
```
selected_model_for_task task_id=task-abc123 agent=planning model=opus-4
selected_model_for_task task_id=task-def456 agent=executor model=sonnet-4
```

### Dashboard

The dashboard shows task details including:
- Agent type
- Model used (in logs)
- Cost and tokens

---

## Best Practices

### 1. **Use Opus for Complex Tasks**
- Planning and analysis
- Strategic decisions
- Complex problem-solving
- Brain orchestration

### 2. **Use Sonnet for Execution**
- Code execution
- Simple tasks
- Fast responses needed
- Cost-sensitive operations

### 3. **Monitor Costs**
- Track usage in dashboard
- Review task costs regularly
- Adjust model selection based on needs

### 4. **Test Different Configurations**
- Start with recommended defaults
- Adjust based on your use case
- Monitor quality vs. cost tradeoff

---

## Troubleshooting

### Model Not Found

**Error:** `Invalid model: opus-4`

**Solution:**
- Check Claude CLI version: `claude --version`
- Verify model name is correct
- Use legacy model names if needed: `opus`, `sonnet`

### Wrong Model Being Used

**Check:**
1. Environment variables are set: `docker-compose exec claude-code-agent env | grep CLAUDE_MODEL`
2. Container restarted after .env changes: `make restart`
3. Logs show correct model: `docker-compose logs | grep selected_model`

### Cost Higher Than Expected

**Solutions:**
- Switch to Sonnet for more agents
- Use Haiku for simple tasks
- Review task assignments (are complex tasks going to executor?)

---

## Summary

**Configuration added:**
- ✅ Model selection per agent type
- ✅ Environment variable configuration
- ✅ Automatic model selection in task worker
- ✅ Logging of model selection
- ✅ Flexible and customizable

**Default setup:**
- Planning Agent → Opus 4 (complex thinking)
- Brain Agent → Opus 4 (orchestration)
- Executor Agent → Sonnet 4 (fast execution)
- Default → Sonnet 4 (cost-effective)

**To use:**
1. Edit `.env` file with your model preferences
2. Restart containers: `make restart`
3. Tasks automatically use configured models
4. Monitor via logs and dashboard

**Optimal for your use case:**
```bash
CLAUDE_MODEL_PLANNING=opus-4    # Complex analysis
CLAUDE_MODEL_BRAIN=opus-4       # Thinking & orchestration
CLAUDE_MODEL_EXECUTOR=sonnet-4  # Fast execution
```
