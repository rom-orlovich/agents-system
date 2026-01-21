# Architecture Refactoring Plan - Modular Webhooks & Agents System

## Overview
This document outlines the architecture refactoring to create a clean, maintainable, and extensible system for webhooks, sub-agents, metrics tracking, and dashboard visualization.

## Design Principles
1. **Plugin-Based Architecture** - Easy to add new webhooks and agents without modifying core code
2. **Registry Pattern** - Central registration for auto-discovery of plugins
3. **Separation of Concerns** - Clear boundaries between components
4. **Type Safety** - Strong typing with Pydantic models
5. **Testability** - Easy to unit test each component in isolation

---

## 1. Webhook Plugin System

### Current Problems
- Webhooks are scattered across multiple files (`routes/jira.py`, `routes/github.py`, etc.)
- Adding new webhook requires modifying main.py and creating new route file
- No standardized interface for webhook handlers
- Difficult to see all available webhooks at a glance

### Proposed Architecture

```
claude-code-cli/services/webhook-server/
├── main.py                          # FastAPI app with plugin auto-discovery
├── core/
│   ├── __init__.py
│   ├── webhook_registry.py          # Central webhook registry
│   ├── webhook_base.py              # Base class for all webhooks
│   └── webhook_validator.py         # Signature validation utilities
├── webhooks/
│   ├── __init__.py                  # Auto-discovers all webhook plugins
│   ├── base.py                      # BaseWebhookHandler abstract class
│   ├── jira_webhook.py              # JiraWebhookHandler
│   ├── github_webhook.py            # GitHubWebhookHandler
│   ├── sentry_webhook.py            # SentryWebhookHandler
│   ├── slack_webhook.py             # SlackWebhookHandler
│   └── [future_webhook.py]          # Easy to add new ones!
└── tests/
    └── webhooks/
        ├── test_jira_webhook.py
        └── test_webhook_registry.py
```

### BaseWebhookHandler Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class WebhookMetadata(BaseModel):
    """Metadata for webhook registration"""
    name: str                    # e.g., "jira"
    endpoint: str                # e.g., "/webhooks/jira"
    description: str             # Human-readable description
    secret_env_var: str          # Environment variable for webhook secret
    enabled: bool = True         # Can be disabled via config

class WebhookResponse(BaseModel):
    """Standardized webhook response"""
    status: str                  # "queued", "ignored", "error"
    task_id: Optional[str]       # Task ID if queued
    message: str                 # Human-readable message
    details: Optional[Dict[str, Any]] = None

class BaseWebhookHandler(ABC):
    """Base class for all webhook handlers"""

    @property
    @abstractmethod
    def metadata(self) -> WebhookMetadata:
        """Return webhook metadata for registration"""
        pass

    @abstractmethod
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature (HMAC, etc.)"""
        pass

    @abstractmethod
    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse and extract relevant data from webhook payload"""
        pass

    @abstractmethod
    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """Determine if this webhook event should be processed"""
        pass

    @abstractmethod
    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """Process the webhook and return response"""
        pass
```

### WebhookRegistry

```python
class WebhookRegistry:
    """Central registry for all webhook handlers"""

    def __init__(self):
        self._handlers: Dict[str, BaseWebhookHandler] = {}

    def register(self, handler: BaseWebhookHandler):
        """Register a webhook handler"""
        metadata = handler.metadata
        if not metadata.enabled:
            logger.info(f"Webhook {metadata.name} is disabled")
            return

        self._handlers[metadata.name] = handler
        logger.info(f"Registered webhook: {metadata.name} at {metadata.endpoint}")

    def get_handler(self, name: str) -> Optional[BaseWebhookHandler]:
        """Get handler by name"""
        return self._handlers.get(name)

    def list_handlers(self) -> List[WebhookMetadata]:
        """List all registered webhook metadata"""
        return [h.metadata for h in self._handlers.values()]

    def auto_discover(self):
        """Auto-discover all webhook handlers in webhooks/ directory"""
        from webhooks import discover_webhooks
        handlers = discover_webhooks()
        for handler in handlers:
            self.register(handler)
```

### Example: JiraWebhookHandler

```python
class JiraWebhookHandler(BaseWebhookHandler):

    @property
    def metadata(self) -> WebhookMetadata:
        return WebhookMetadata(
            name="jira",
            endpoint="/webhooks/jira",
            description="Handle Jira issue events (created, updated)",
            secret_env_var="JIRA_WEBHOOK_SECRET",
            enabled=True
        )

    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        secret = os.getenv(self.metadata.secret_env_var)
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract Jira issue data"""
        issue = payload.get("issue", {})
        return {
            "issue_key": issue.get("key"),
            "event_type": payload.get("webhookEvent"),
            "description": issue.get("fields", {}).get("description"),
            "labels": issue.get("fields", {}).get("labels", []),
        }

    async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
        """Process if has AI-Fix label or Sentry-created"""
        labels = parsed_data.get("labels", [])
        description = parsed_data.get("description", "")

        return "AI-Fix" in labels or "Sentry Issue:" in description

    async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
        """Queue task for planning agent"""
        task_id = await task_queue.enqueue_planning_task(
            source=TaskSource.JIRA,
            issue_key=parsed_data["issue_key"],
            description=parsed_data["description"]
        )

        return WebhookResponse(
            status="queued",
            task_id=task_id,
            message=f"Queued Jira issue {parsed_data['issue_key']} for processing"
        )
```

### Benefits
- ✅ Add new webhook by creating single file implementing BaseWebhookHandler
- ✅ Auto-discovery - no need to modify main.py
- ✅ Consistent interface across all webhooks
- ✅ Easy to test in isolation
- ✅ Easy to disable/enable webhooks via config
- ✅ Self-documenting via metadata

---

## 2. Sub-Agent Registry System

### Current Problems
- Agents are scattered across different systems with inconsistent patterns
- No central place to see all available agents
- Adding new agent requires modifying worker code
- No standardized interface for agents

### Proposed Architecture

```
claude-code-cli/agents/
├── core/
│   ├── __init__.py
│   ├── agent_registry.py            # Central agent registry
│   ├── agent_base.py                # Base class for all agents
│   └── agent_metrics.py             # Agent-specific metrics tracking
├── sub_agents/
│   ├── __init__.py                  # Auto-discovers all agents
│   ├── base.py                      # BaseAgent abstract class
│   ├── planning_agent.py            # Planning agent implementation
│   ├── executor_agent.py            # Code execution agent
│   ├── discovery_agent.py           # Repository discovery agent
│   ├── cicd_agent.py                # CI/CD monitoring agent
│   ├── code_review_agent.py         # Code review agent
│   └── [future_agent.py]            # Easy to add new ones!
└── tests/
    └── sub_agents/
        ├── test_planning_agent.py
        └── test_agent_registry.py
```

### BaseAgent Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from enum import Enum

class AgentCapability(str, Enum):
    """Agent capabilities"""
    PLANNING = "planning"
    EXECUTION = "execution"
    DISCOVERY = "discovery"
    REVIEW = "review"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"

class AgentMetadata(BaseModel):
    """Metadata for agent registration"""
    name: str                           # e.g., "planning-agent"
    display_name: str                   # e.g., "Planning Agent"
    description: str                    # Human-readable description
    capabilities: List[AgentCapability] # What can this agent do
    version: str = "1.0.0"              # Agent version
    enabled: bool = True                # Can be disabled via config
    max_retries: int = 3                # Max retry attempts
    timeout_seconds: int = 3600         # Max execution time

class AgentContext(BaseModel):
    """Context passed to agent for execution"""
    task_id: str
    session_id: str                     # Unique session ID for this execution
    task: Task                          # Full task object
    config: Dict[str, Any]              # Agent-specific config
    previous_result: Optional[Any] = None  # Result from previous agent in chain

class AgentResult(BaseModel):
    """Standardized agent result"""
    success: bool
    agent_name: str
    session_id: str
    output: Dict[str, Any]              # Agent-specific output
    metrics: Dict[str, Any]             # Execution metrics (tokens, cost, etc.)
    error: Optional[str] = None
    next_agent: Optional[str] = None    # Chain to next agent if needed

class BaseAgent(ABC):
    """Base class for all sub-agents"""

    @property
    @abstractmethod
    def metadata(self) -> AgentMetadata:
        """Return agent metadata for registration"""
        pass

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's main logic"""
        pass

    async def pre_execute(self, context: AgentContext) -> bool:
        """Pre-execution validation (return False to skip execution)"""
        return True

    async def post_execute(self, result: AgentResult) -> AgentResult:
        """Post-execution processing"""
        return result

    async def on_error(self, context: AgentContext, error: Exception) -> AgentResult:
        """Error handling"""
        logger.error(f"Agent {self.metadata.name} failed: {error}")
        return AgentResult(
            success=False,
            agent_name=self.metadata.name,
            session_id=context.session_id,
            output={},
            metrics={},
            error=str(error)
        )
```

### AgentRegistry

```python
class AgentRegistry:
    """Central registry for all agents"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._execution_history: List[Dict[str, Any]] = []

    def register(self, agent: BaseAgent):
        """Register an agent"""
        metadata = agent.metadata
        if not metadata.enabled:
            logger.info(f"Agent {metadata.name} is disabled")
            return

        self._agents[metadata.name] = agent
        logger.info(f"Registered agent: {metadata.name} ({metadata.display_name})")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        return self._agents.get(name)

    def list_agents(self) -> List[AgentMetadata]:
        """List all registered agent metadata"""
        return [a.metadata for a in self._agents.values()]

    def get_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Get all agents with specific capability"""
        return [
            agent for agent in self._agents.values()
            if capability in agent.metadata.capabilities
        ]

    async def execute_agent(self, agent_name: str, context: AgentContext) -> AgentResult:
        """Execute an agent and track metrics"""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")

        start_time = time.time()

        try:
            # Pre-execution check
            if not await agent.pre_execute(context):
                return AgentResult(
                    success=False,
                    agent_name=agent_name,
                    session_id=context.session_id,
                    output={},
                    metrics={},
                    error="Pre-execution check failed"
                )

            # Execute
            result = await agent.execute(context)

            # Post-execution processing
            result = await agent.post_execute(result)

            # Track metrics
            duration = time.time() - start_time
            await self._track_execution(agent_name, context, result, duration)

            return result

        except Exception as e:
            logger.exception(f"Agent {agent_name} execution failed")
            result = await agent.on_error(context, e)
            duration = time.time() - start_time
            await self._track_execution(agent_name, context, result, duration)
            return result

    async def _track_execution(
        self,
        agent_name: str,
        context: AgentContext,
        result: AgentResult,
        duration: float
    ):
        """Track agent execution in metrics and history"""
        # Update Prometheus metrics
        metrics.agent_execution_counter.labels(
            agent=agent_name,
            status="success" if result.success else "failed"
        ).inc()

        metrics.agent_execution_duration.labels(agent=agent_name).observe(duration)

        if result.metrics.get("total_cost"):
            metrics.agent_cost_total.labels(agent=agent_name).inc(
                result.metrics["total_cost"]
            )

        # Store in execution history
        execution_record = {
            "agent_name": agent_name,
            "session_id": context.session_id,
            "task_id": context.task_id,
            "success": result.success,
            "duration_seconds": duration,
            "metrics": result.metrics,
            "timestamp": datetime.now().isoformat()
        }
        self._execution_history.append(execution_record)

        # Store in Redis for dashboard
        await redis_client.lpush(
            f"agent_executions:{context.task_id}",
            json.dumps(execution_record)
        )

    def auto_discover(self):
        """Auto-discover all agents in sub_agents/ directory"""
        from sub_agents import discover_agents
        agents = discover_agents()
        for agent in agents:
            self.register(agent)
```

### Example: PlanningAgent

```python
class PlanningAgent(BaseAgent):

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="planning-agent",
            display_name="Planning Agent",
            description="Creates implementation plans for bug fixes and features",
            capabilities=[AgentCapability.PLANNING, AgentCapability.ANALYSIS],
            version="2.0.0",
            enabled=True,
            max_retries=3,
            timeout_seconds=1800
        )

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute planning logic"""
        session_id = context.session_id
        task = context.task

        # Load planning skill
        skill = self._load_skill("plan-changes")

        # Build context for Claude
        claude_context = self._build_context(task)

        # Call Claude Code CLI with MCP tools
        result = await self._call_claude(
            session_id=session_id,
            skill=skill,
            context=claude_context
        )

        # Parse plan from Claude output
        plan = self._parse_plan(result.output)

        # Create GitHub PR with plan
        pr_url = await self._create_plan_pr(task, plan)

        return AgentResult(
            success=True,
            agent_name=self.metadata.name,
            session_id=session_id,
            output={
                "plan": plan.model_dump(),
                "pr_url": pr_url
            },
            metrics={
                "tokens_used": result.usage.input_tokens + result.usage.output_tokens,
                "total_cost": result.usage.total_cost,
                "duration_seconds": result.duration
            },
            next_agent="executor-agent"  # Chain to executor after approval
        )
```

### Benefits
- ✅ Add new agent by creating single file implementing BaseAgent
- ✅ Auto-discovery - no need to modify worker code
- ✅ Consistent interface across all agents
- ✅ Built-in metrics tracking per agent
- ✅ Easy to test in isolation
- ✅ Agent chaining support
- ✅ Self-documenting via metadata

---

## 3. Enhanced Metrics & Tracking

### New Metrics to Add

```python
# claude-code-cli/shared/enhanced_metrics.py

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional

# Existing metrics (keep as-is)
# ...

# NEW: Agent-specific metrics
agent_execution_counter = Counter(
    'ai_agent_execution_total',
    'Total agent executions',
    ['agent', 'status', 'task_type']  # Added task_type dimension
)

agent_execution_duration = Histogram(
    'ai_agent_execution_duration_seconds',
    'Agent execution duration',
    ['agent', 'task_type'],
    buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600)
)

agent_cost_total = Counter(
    'ai_agent_cost_total_usd',
    'Total cost in USD per agent',
    ['agent', 'model']  # Track which model used
)

agent_token_usage = Counter(
    'ai_agent_tokens_total',
    'Total tokens used per agent',
    ['agent', 'token_type']  # input/output/cache_read/cache_write
)

# NEW: Session tracking
session_active = Gauge(
    'ai_agent_sessions_active',
    'Currently active agent sessions',
    ['agent']
)

session_duration = Histogram(
    'ai_agent_session_duration_seconds',
    'Session duration from start to completion',
    ['agent', 'task_type'],
    buckets=(60, 300, 600, 1200, 1800, 3600, 7200)
)

# NEW: Task success rate per agent
task_success_rate = Gauge(
    'ai_agent_task_success_rate',
    'Success rate (0-1) per agent over last 100 tasks',
    ['agent']
)

# NEW: Agent chain tracking
agent_chain_depth = Histogram(
    'ai_agent_chain_depth',
    'Number of agents in execution chain',
    buckets=(1, 2, 3, 4, 5, 10)
)
```

### Enhanced Task Model

```python
# claude-code-cli/shared/models.py

class AgentExecution(BaseModel):
    """Tracks individual agent execution within a task"""
    agent_name: str
    session_id: str                    # NEW: Session ID
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    success: bool
    error: Optional[str]

    # NEW: Claude usage metrics
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0         # Prompt caching
    cache_write_tokens: int = 0
    total_cost_usd: float = 0.0
    model_used: str = ""               # e.g., "claude-sonnet-4.5"

    # NEW: Agent-specific output
    output: Dict[str, Any] = {}
    next_agent: Optional[str] = None

class Task(BaseModel):
    """Enhanced task model with agent execution tracking"""
    task_id: str
    status: TaskStatus
    source: TaskSource

    # ... existing fields ...

    # NEW: Agent execution history
    agent_executions: List[AgentExecution] = []
    current_agent: Optional[str] = None
    current_session_id: Optional[str] = None

    # NEW: Cost tracking
    total_cost_usd: float = 0.0
    total_tokens_used: int = 0

    def add_agent_execution(self, execution: AgentExecution):
        """Add agent execution to history and update totals"""
        self.agent_executions.append(execution)
        self.total_cost_usd += execution.total_cost_usd
        self.total_tokens_used += (
            execution.input_tokens +
            execution.output_tokens +
            execution.cache_read_tokens +
            execution.cache_write_tokens
        )

    def get_agent_chain(self) -> List[str]:
        """Get list of agents that executed in order"""
        return [exec.agent_name for exec in self.agent_executions]
```

### Dashboard Data API

```python
# claude-code-cli/services/webhook-server/routes/dashboard_api.py

from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/tasks")
async def get_tasks(
    agent: Optional[str] = None,           # Filter by agent
    status: Optional[TaskStatus] = None,
    source: Optional[TaskSource] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=50, le=500)
):
    """Get tasks with filtering"""
    tasks = await task_queue.list_tasks(
        agent=agent,
        status=status,
        source=source,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return {"tasks": tasks}

@router.get("/agents")
async def get_agents():
    """Get all registered agents with metadata"""
    from agents.core.agent_registry import agent_registry
    agents = agent_registry.list_agents()
    return {"agents": [a.model_dump() for a in agents]}

@router.get("/agent-stats")
async def get_agent_stats(agent: Optional[str] = None):
    """Get agent execution statistics"""
    # Query Redis for agent execution history
    stats = await redis_client.get_agent_stats(agent)
    return {"stats": stats}

@router.get("/cost-breakdown")
async def get_cost_breakdown(
    agent: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_by: str = Query(default="agent", regex="^(agent|day|task_type)$")
):
    """Get cost breakdown with grouping"""
    costs = await redis_client.get_cost_breakdown(
        agent=agent,
        start_date=start_date or datetime.now() - timedelta(days=30),
        end_date=end_date or datetime.now(),
        group_by=group_by
    )
    return {"costs": costs}

@router.get("/agent-chain-analytics")
async def get_agent_chain_analytics():
    """Get analytics on agent execution chains"""
    chains = await redis_client.get_agent_chains()

    # Analyze common patterns
    chain_patterns = {}
    for chain in chains:
        pattern = " → ".join(chain["agents"])
        if pattern not in chain_patterns:
            chain_patterns[pattern] = {
                "count": 0,
                "avg_duration": 0,
                "success_rate": 0
            }
        chain_patterns[pattern]["count"] += 1

    return {"chain_patterns": chain_patterns}
```

---

## 4. Dashboard Implementation

### Technology Stack
- **Framework**: Next.js 14 (App Router)
- **UI Library**: shadcn/ui + Radix UI
- **Charts**: Recharts
- **State Management**: React Query (TanStack Query)
- **Styling**: Tailwind CSS
- **Real-time**: Server-Sent Events (SSE) or WebSockets

### Project Structure

```
claude-code-cli/services/dashboard/
├── package.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── app/
│   ├── layout.tsx                   # Root layout
│   ├── page.tsx                     # Home page (task list)
│   ├── tasks/
│   │   └── [id]/page.tsx            # Task detail page
│   ├── agents/
│   │   └── page.tsx                 # Agents overview
│   └── analytics/
│       └── page.tsx                 # Cost analytics
├── components/
│   ├── ui/                          # shadcn/ui components
│   ├── TaskList.tsx                 # Task list with filtering
│   ├── TaskCard.tsx                 # Individual task card
│   ├── AgentCard.tsx                # Agent info card
│   ├── AgentExecutionTimeline.tsx   # Timeline of agent executions
│   ├── CostChart.tsx                # Cost breakdown chart
│   ├── AgentFilter.tsx              # Agent filter dropdown
│   └── MetricsOverview.tsx          # Key metrics dashboard
├── lib/
│   ├── api.ts                       # API client
│   ├── types.ts                     # TypeScript types
│   └── utils.ts                     # Utility functions
└── hooks/
    ├── useTasks.ts                  # React Query hook for tasks
    ├── useAgents.ts                 # React Query hook for agents
    └── useMetrics.ts                # React Query hook for metrics
```

### Key Components

#### 1. Task List with Agent Filtering

```typescript
// components/TaskList.tsx
interface TaskListProps {
  initialTasks: Task[];
}

export function TaskList({ initialTasks }: TaskListProps) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<TaskStatus | null>(null);
  const [dateRange, setDateRange] = useState({ start: null, end: null });

  const { data: tasks, isLoading } = useTasks({
    agent: selectedAgent,
    status: selectedStatus,
    startDate: dateRange.start,
    endDate: dateRange.end,
    refetchInterval: 5000  // Real-time updates every 5s
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <AgentFilter value={selectedAgent} onChange={setSelectedAgent} />
        <StatusFilter value={selectedStatus} onChange={setSelectedStatus} />
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      <div className="grid gap-4">
        {tasks?.map(task => (
          <TaskCard key={task.task_id} task={task} />
        ))}
      </div>
    </div>
  );
}
```

#### 2. Agent Execution Timeline

```typescript
// components/AgentExecutionTimeline.tsx
interface AgentExecutionTimelineProps {
  executions: AgentExecution[];
}

export function AgentExecutionTimeline({ executions }: AgentExecutionTimelineProps) {
  return (
    <div className="relative">
      {executions.map((exec, idx) => (
        <div key={exec.session_id} className="flex items-start gap-4 mb-6">
          {/* Timeline dot */}
          <div className={cn(
            "w-3 h-3 rounded-full mt-2",
            exec.success ? "bg-green-500" : "bg-red-500"
          )} />

          {/* Execution card */}
          <Card className="flex-1">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{exec.agent_name}</CardTitle>
                <Badge variant={exec.success ? "success" : "destructive"}>
                  {exec.success ? "Success" : "Failed"}
                </Badge>
              </div>
              <CardDescription>
                Session: {exec.session_id}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Duration</p>
                  <p className="font-medium">{exec.duration_seconds}s</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Cost</p>
                  <p className="font-medium">${exec.total_cost_usd.toFixed(4)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Tokens</p>
                  <p className="font-medium">
                    {exec.input_tokens + exec.output_tokens}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Model</p>
                  <p className="font-medium">{exec.model_used}</p>
                </div>
              </div>

              {exec.error && (
                <Alert variant="destructive" className="mt-4">
                  <AlertDescription>{exec.error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>
      ))}
    </div>
  );
}
```

#### 3. Cost Breakdown Chart

```typescript
// components/CostChart.tsx
interface CostChartProps {
  groupBy: 'agent' | 'day' | 'task_type';
}

export function CostChart({ groupBy }: CostChartProps) {
  const { data: costData } = useCostBreakdown({ groupBy });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost Breakdown</CardTitle>
        <CardDescription>
          Total costs grouped by {groupBy}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={costData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip
              formatter={(value) => `$${Number(value).toFixed(2)}`}
            />
            <Bar dataKey="cost" fill="hsl(var(--primary))" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

#### 4. Metrics Overview Dashboard

```typescript
// components/MetricsOverview.tsx
export function MetricsOverview() {
  const { data: agents } = useAgents();
  const { data: stats } = useAgentStats();

  const totalTasks = stats?.total_tasks ?? 0;
  const successRate = stats?.success_rate ?? 0;
  const totalCost = stats?.total_cost ?? 0;
  const avgDuration = stats?.avg_duration ?? 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{totalTasks}</div>
          <p className="text-xs text-muted-foreground">
            Last 30 days
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{(successRate * 100).toFixed(1)}%</div>
          <Progress value={successRate * 100} className="mt-2" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">${totalCost.toFixed(2)}</div>
          <p className="text-xs text-muted-foreground">
            Last 30 days
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{Math.round(avgDuration)}s</div>
          <p className="text-xs text-muted-foreground">
            Per task
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Dashboard Pages

#### Home Page (Task List)
```typescript
// app/page.tsx
export default async function HomePage() {
  const initialTasks = await fetchTasks();

  return (
    <div className="container py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Agent System</h1>
        <p className="text-muted-foreground">
          Monitor and manage AI agent tasks in real-time
        </p>
      </div>

      <MetricsOverview />
      <TaskList initialTasks={initialTasks} />
    </div>
  );
}
```

#### Agent Analytics Page
```typescript
// app/analytics/page.tsx
export default function AnalyticsPage() {
  const [groupBy, setGroupBy] = useState<'agent' | 'day' | 'task_type'>('agent');

  return (
    <div className="container py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Cost Analytics</h1>
        <p className="text-muted-foreground">
          Analyze agent costs and performance
        </p>
      </div>

      <div className="flex gap-2">
        <Button
          variant={groupBy === 'agent' ? 'default' : 'outline'}
          onClick={() => setGroupBy('agent')}
        >
          By Agent
        </Button>
        <Button
          variant={groupBy === 'day' ? 'default' : 'outline'}
          onClick={() => setGroupBy('day')}
        >
          By Day
        </Button>
        <Button
          variant={groupBy === 'task_type' ? 'default' : 'outline'}
          onClick={() => setGroupBy('task_type')}
        >
          By Task Type
        </Button>
      </div>

      <CostChart groupBy={groupBy} />
      <AgentChainAnalytics />
    </div>
  );
}
```

---

## 5. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
1. ✅ Create webhook plugin system
   - BaseWebhookHandler abstract class
   - WebhookRegistry with auto-discovery
   - Update main.py to use registry
2. ✅ Create agent registry system
   - BaseAgent abstract class
   - AgentRegistry with auto-discovery
   - Update worker to use registry
3. ✅ Enhance metrics and task models
   - Add new Prometheus metrics
   - Update Task model with agent_executions
   - Create AgentExecution model

### Phase 2: Migrate Existing Code (Week 2)
1. ✅ Migrate webhook handlers
   - JiraWebhookHandler
   - GitHubWebhookHandler
   - SentryWebhookHandler
   - SlackWebhookHandler
2. ✅ Migrate agents
   - PlanningAgent
   - ExecutorAgent
   - DiscoveryAgent (if separate)
3. ✅ Update all references to use new registry

### Phase 3: Dashboard (Week 3)
1. ✅ Set up Next.js project
2. ✅ Create API endpoints
3. ✅ Build core components
4. ✅ Implement filtering and charts
5. ✅ Add real-time updates

### Phase 4: Testing & Documentation (Week 4)
1. ✅ Write TDD tests for all components
2. ✅ Update documentation
3. ✅ Integration testing
4. ✅ Performance testing

---

## 6. Testing Strategy (TDD)

### Webhook Tests

```python
# tests/webhooks/test_jira_webhook.py
import pytest
from webhooks.jira_webhook import JiraWebhookHandler

@pytest.mark.asyncio
async def test_jira_webhook_should_process_ai_fix_label():
    handler = JiraWebhookHandler()

    parsed_data = {
        "issue_key": "TEST-123",
        "labels": ["AI-Fix", "bug"],
        "description": "Test issue"
    }

    should_process = await handler.should_process(parsed_data)
    assert should_process is True

@pytest.mark.asyncio
async def test_jira_webhook_should_process_sentry_issue():
    handler = JiraWebhookHandler()

    parsed_data = {
        "issue_key": "TEST-123",
        "labels": [],
        "description": "Sentry Issue: 12345\nError details..."
    }

    should_process = await handler.should_process(parsed_data)
    assert should_process is True

@pytest.mark.asyncio
async def test_jira_webhook_should_not_process_regular_issue():
    handler = JiraWebhookHandler()

    parsed_data = {
        "issue_key": "TEST-123",
        "labels": ["bug"],
        "description": "Regular issue"
    }

    should_process = await handler.should_process(parsed_data)
    assert should_process is False

@pytest.mark.asyncio
async def test_jira_webhook_validate_signature():
    handler = JiraWebhookHandler()

    payload = b'{"issue": {"key": "TEST-123"}}'
    signature = "valid_signature_here"

    is_valid = await handler.validate_signature(payload, signature)
    assert is_valid is True
```

### Agent Tests

```python
# tests/sub_agents/test_planning_agent.py
import pytest
from sub_agents.planning_agent import PlanningAgent
from agents.core.agent_base import AgentContext

@pytest.mark.asyncio
async def test_planning_agent_execution():
    agent = PlanningAgent()

    context = AgentContext(
        task_id="task-123",
        session_id="session-456",
        task=mock_task,
        config={}
    )

    result = await agent.execute(context)

    assert result.success is True
    assert result.agent_name == "planning-agent"
    assert result.session_id == "session-456"
    assert "plan" in result.output
    assert "pr_url" in result.output
    assert result.metrics["total_cost"] > 0

@pytest.mark.asyncio
async def test_planning_agent_error_handling():
    agent = PlanningAgent()

    # Simulate error condition
    context = AgentContext(
        task_id="task-123",
        session_id="session-456",
        task=invalid_task,  # Invalid task
        config={}
    )

    result = await agent.execute(context)

    assert result.success is False
    assert result.error is not None
```

### Registry Tests

```python
# tests/core/test_agent_registry.py
import pytest
from agents.core.agent_registry import AgentRegistry
from sub_agents.planning_agent import PlanningAgent

def test_agent_registration():
    registry = AgentRegistry()
    agent = PlanningAgent()

    registry.register(agent)

    assert registry.get_agent("planning-agent") is not None
    assert len(registry.list_agents()) == 1

def test_agent_auto_discovery():
    registry = AgentRegistry()

    registry.auto_discover()

    agents = registry.list_agents()
    assert len(agents) > 0
    assert any(a.name == "planning-agent" for a in agents)

@pytest.mark.asyncio
async def test_agent_execution_tracking():
    registry = AgentRegistry()
    agent = PlanningAgent()
    registry.register(agent)

    context = AgentContext(
        task_id="task-123",
        session_id="session-456",
        task=mock_task,
        config={}
    )

    result = await registry.execute_agent("planning-agent", context)

    assert result.success is True
    # Verify metrics were tracked
    assert len(registry._execution_history) == 1
```

---

## 7. Documentation Updates

### Business Logic Documentation

Will update the following files:
- `BUSINESS_LOGIC.md` - Add webhook and agent plugin architecture
- `ARCHITECTURE.md` - Update with new component structure
- `DEVELOPMENT.md` - Add guide for creating new webhooks and agents
- `API.md` - Document new dashboard API endpoints

### Developer Guide: Adding New Webhook

```markdown
## Adding a New Webhook

1. Create new file in `webhooks/` directory:
   ```python
   # webhooks/custom_webhook.py
   from webhooks.base import BaseWebhookHandler, WebhookMetadata

   class CustomWebhookHandler(BaseWebhookHandler):
       @property
       def metadata(self) -> WebhookMetadata:
           return WebhookMetadata(
               name="custom",
               endpoint="/webhooks/custom",
               description="Handle custom service events",
               secret_env_var="CUSTOM_WEBHOOK_SECRET"
           )

       async def validate_signature(self, payload: bytes, signature: str) -> bool:
           # Implement signature validation
           pass

       async def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
           # Extract relevant data
           pass

       async def should_process(self, parsed_data: Dict[str, Any]) -> bool:
           # Determine if should process
           pass

       async def handle(self, parsed_data: Dict[str, Any]) -> WebhookResponse:
           # Process webhook
           pass
   ```

2. Add tests:
   ```python
   # tests/webhooks/test_custom_webhook.py
   import pytest
   from webhooks.custom_webhook import CustomWebhookHandler

   @pytest.mark.asyncio
   async def test_custom_webhook_should_process():
       handler = CustomWebhookHandler()
       # ... test cases
   ```

3. That's it! The webhook will be auto-discovered and registered.
```

### Developer Guide: Adding New Agent

```markdown
## Adding a New Agent

1. Create new file in `sub_agents/` directory:
   ```python
   # sub_agents/custom_agent.py
   from agents.core.agent_base import BaseAgent, AgentMetadata, AgentCapability

   class CustomAgent(BaseAgent):
       @property
       def metadata(self) -> AgentMetadata:
           return AgentMetadata(
               name="custom-agent",
               display_name="Custom Agent",
               description="Performs custom task",
               capabilities=[AgentCapability.ANALYSIS]
           )

       async def execute(self, context: AgentContext) -> AgentResult:
           # Implement agent logic
           pass
   ```

2. Add tests:
   ```python
   # tests/sub_agents/test_custom_agent.py
   import pytest
   from sub_agents.custom_agent import CustomAgent

   @pytest.mark.asyncio
   async def test_custom_agent_execution():
       agent = CustomAgent()
       # ... test cases
   ```

3. That's it! The agent will be auto-discovered and registered.
```

---

## Summary

This refactoring will create a **clean, maintainable, and extensible** system where:

✅ **Adding new webhooks** is as simple as creating a single file
✅ **Adding new agents** is as simple as creating a single file
✅ **All metrics** track which agent executed each task, with session IDs
✅ **Dashboard** provides filtering by agent and cost visualization
✅ **TDD tests** ensure quality and prevent regressions
✅ **Documentation** is comprehensive and up-to-date

The plugin-based architecture with auto-discovery means **zero changes to core code** when adding new capabilities. Everything is type-safe, well-tested, and self-documenting through metadata.
