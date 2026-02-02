# Autonomous Self-Healing Agent System - Implementation Plan

## Vision Overview

Build an autonomous system that:
1. **QA Agent** - Runs application flows in Docker, detects bugs, opens tickets
2. **Product Agent** - Creates development tasks based on features/requirements
3. **Log Monitor Agent** - Watches application logs, detects errors, triggers fixes
4. **Task Classifier Agent** - Analyzes tasks, classifies (story/task/bug), breaks down large tasks
5. **Self-Healing Loop** - Bug detected → Ticket created → PR opened → Fix applied → Verified

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AUTONOMOUS SELF-HEALING SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  QA Agent    │    │ Log Monitor  │    │Product Agent │                  │
│  │  (E2E Tests) │    │   Agent      │    │(Feature Spec)│                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    TASK CLASSIFIER AGENT                     │           │
│  │         (Analyzes, Classifies: Story/Task/Bug)              │           │
│  │         (Breaks down large tasks into subtasks)             │           │
│  └─────────────────────────────┬───────────────────────────────┘           │
│                                │                                            │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                      JIRA (Ticket Store)                     │           │
│  └─────────────────────────────┬───────────────────────────────┘           │
│                                │ Webhook                                    │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │              EXISTING AGENT-BOT PIPELINE                     │           │
│  │  Brain → Planning → Executor → Verifier → GitHub PR          │           │
│  └─────────────────────────────┬───────────────────────────────┘           │
│                                │                                            │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                   DEPLOYED APPLICATION                       │           │
│  │              (Auto-deployed after PR merge)                  │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                │                                            │
│                  ┌─────────────┴─────────────┐                             │
│                  ▼                           ▼                              │
│           QA Agent runs               Log Monitor watches                   │
│           E2E tests again             for new errors                        │
│                  │                           │                              │
│                  └───────────────────────────┘                             │
│                                │                                            │
│                       LOOP CONTINUES                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Log Monitor Agent (Week 1-2)

### Goal
Monitor application logs in Docker containers, detect errors, and automatically create Jira tickets.

### New Components

#### 1.1 Log Monitor Service (`log-monitor/`)

```
agent-bot/
└── log-monitor/
    ├── Dockerfile
    ├── pyproject.toml
    ├── core/
    │   ├── __init__.py
    │   ├── config.py           # Configuration
    │   ├── models.py           # Log event models
    │   ├── log_collector.py    # Docker log collection
    │   ├── error_detector.py   # Pattern matching + AI classification
    │   └── ticket_creator.py   # Jira ticket creation
    ├── workers/
    │   ├── __init__.py
    │   └── monitor_worker.py   # Main monitoring loop
    └── tests/
        ├── conftest.py
        ├── test_log_collector.py
        └── test_error_detector.py
```

#### 1.2 Log Collector Implementation

```python
# log-monitor/core/log_collector.py
import asyncio
import docker
from datetime import datetime, timedelta

class DockerLogCollector:
    def __init__(self, containers: list[str], lookback_minutes: int = 5):
        self.client = docker.from_env()
        self.containers = containers
        self.lookback = timedelta(minutes=lookback_minutes)

    async def stream_logs(self) -> AsyncIterator[LogEvent]:
        for container_name in self.containers:
            container = self.client.containers.get(container_name)
            since = datetime.utcnow() - self.lookback

            for log_line in container.logs(
                stream=True,
                since=since,
                timestamps=True
            ):
                yield LogEvent(
                    container=container_name,
                    timestamp=extract_timestamp(log_line),
                    message=log_line.decode('utf-8'),
                    level=detect_log_level(log_line)
                )
```

#### 1.3 Error Detector with AI Classification

```python
# log-monitor/core/error_detector.py
from anthropic import AsyncAnthropic

class ErrorDetector:
    ERROR_PATTERNS = [
        r"(?i)error[:\s]",
        r"(?i)exception[:\s]",
        r"(?i)failed[:\s]",
        r"(?i)traceback",
        r"(?i)panic:",
        r"HTTP [45]\d{2}",
    ]

    async def classify_error(self, log_events: list[LogEvent]) -> ErrorClassification:
        """Use Claude to classify error severity and suggest ticket type."""
        context = "\n".join([e.message for e in log_events[-50:]])

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{
                "role": "user",
                "content": f"""Analyze these application logs and classify the error:

{context}

Respond with JSON:
{{
  "is_error": true/false,
  "severity": "critical|high|medium|low",
  "error_type": "bug|performance|infrastructure",
  "title": "Brief error title",
  "description": "Detailed description",
  "affected_component": "component name",
  "suggested_fix": "potential fix approach"
}}"""
            }]
        )
        return ErrorClassification.model_validate_json(response.content[0].text)
```

#### 1.4 Jira Ticket Creator

```python
# log-monitor/core/ticket_creator.py
import httpx

class TicketCreator:
    def __init__(self, jira_api_url: str = "http://jira-api:3002"):
        self.jira_url = jira_api_url

    async def create_bug_ticket(self, error: ErrorClassification) -> str:
        """Create Jira bug ticket from detected error."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.jira_url}/issues",
                json={
                    "project": "PROJ",
                    "issuetype": "Bug",
                    "summary": f"[Auto-detected] {error.title}",
                    "description": self._format_description(error),
                    "priority": self._map_severity(error.severity),
                    "labels": ["AI-Fix", "auto-detected", error.error_type],
                }
            )
            return response.json()["key"]
```

### Docker Compose Addition

```yaml
# Add to docker-compose.yml
log-monitor:
  build:
    context: ./log-monitor
    dockerfile: Dockerfile
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro  # Docker socket for log access
  environment:
    - MONITORED_CONTAINERS=app-web,app-api,app-worker
    - JIRA_API_URL=http://jira-api:3002
    - CHECK_INTERVAL_SECONDS=30
    - ERROR_COOLDOWN_MINUTES=60  # Prevent duplicate tickets
  depends_on:
    - jira-api
    - redis
  networks:
    - agent-network
```

---

## Phase 2: QA Agent (Week 3-4)

### Goal
Run E2E tests/flows against the application in Docker, report failures as bugs.

### New Components

#### 2.1 QA Agent Service (`qa-agent/`)

```
agent-bot/
└── qa-agent/
    ├── Dockerfile
    ├── pyproject.toml
    ├── core/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── models.py
    │   ├── flow_executor.py    # Runs test flows
    │   ├── browser_runner.py   # Playwright/Selenium
    │   └── report_generator.py # Test result analysis
    ├── flows/
    │   ├── __init__.py
    │   ├── base_flow.py
    │   ├── login_flow.py
    │   ├── checkout_flow.py
    │   └── ...
    ├── workers/
    │   ├── __init__.py
    │   └── qa_worker.py
    └── tests/
```

#### 2.2 Flow Executor with AI

```python
# qa-agent/core/flow_executor.py
from playwright.async_api import async_playwright

class FlowExecutor:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def execute_flow(self, flow: TestFlow) -> FlowResult:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            steps_results = []
            for step in flow.steps:
                try:
                    result = await self._execute_step(page, step)
                    steps_results.append(result)
                except Exception as e:
                    # Capture screenshot and DOM state
                    screenshot = await page.screenshot()
                    dom_state = await page.content()

                    steps_results.append(StepResult(
                        step=step,
                        success=False,
                        error=str(e),
                        screenshot=screenshot,
                        dom_state=dom_state
                    ))
                    break

            await browser.close()
            return FlowResult(flow=flow, steps=steps_results)

    async def analyze_failure(self, result: FlowResult) -> BugReport:
        """Use Claude to analyze test failure and generate bug report."""
        failed_step = next(s for s in result.steps if not s.success)

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{
                "role": "user",
                "content": f"""Analyze this E2E test failure:

Flow: {result.flow.name}
Failed Step: {failed_step.step.description}
Error: {failed_step.error}
DOM State: {failed_step.dom_state[:5000]}

Generate a bug report with:
1. Clear title
2. Steps to reproduce
3. Expected vs actual behavior
4. Suggested component to investigate
5. Potential root cause"""
            }]
        )
        return BugReport.parse(response.content[0].text)
```

#### 2.3 AI-Driven Flow Generation

```python
# qa-agent/core/flow_generator.py
class AIFlowGenerator:
    """Generate test flows by analyzing the application."""

    async def generate_flows_from_app(self, app_url: str) -> list[TestFlow]:
        """Crawl app and generate meaningful test flows."""
        # 1. Crawl the application
        pages = await self._crawl_app(app_url)

        # 2. Ask Claude to generate test scenarios
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{
                "role": "user",
                "content": f"""Based on these application pages, generate E2E test flows:

Pages found:
{json.dumps(pages, indent=2)}

Generate 5-10 critical user flows as JSON:
[{{
  "name": "flow_name",
  "description": "what this tests",
  "priority": "critical|high|medium",
  "steps": [
    {{"action": "navigate|click|fill|assert", "target": "selector", "value": "..."}}
  ]
}}]"""
            }]
        )
        return [TestFlow.model_validate(f) for f in json.loads(response.content[0].text)]
```

### Docker Compose Addition

```yaml
qa-agent:
  build:
    context: ./qa-agent
    dockerfile: Dockerfile
  environment:
    - TARGET_APP_URL=http://app-web:3000
    - RUN_INTERVAL_HOURS=6
    - JIRA_API_URL=http://jira-api:3002
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  depends_on:
    - app-web  # Your application
    - jira-api
  networks:
    - agent-network
```

---

## Phase 3: Task Classifier Agent (Week 5-6)

### Goal
Analyze incoming tasks/descriptions and classify them as Story/Task/Bug, then break down large items.

### New Agent Definition

#### 3.1 Task Classifier Agent (`.claude/agents/task-classifier.md`)

```markdown
# Task Classifier Agent

## Role
Analyze task descriptions and classify them appropriately, then break down large tasks into manageable subtasks.

## Capabilities
1. Classify tasks as: Epic, Story, Task, Bug, Spike
2. Estimate task complexity (XS, S, M, L, XL)
3. Break down large tasks (L, XL) into subtasks
4. Identify dependencies between tasks
5. Suggest appropriate labels and components

## Classification Rules

### Epic (>2 weeks work)
- Major feature or initiative
- Requires multiple stories
- Cross-functional impact

### Story (1-5 days work)
- User-facing feature
- Has clear acceptance criteria
- Delivers business value

### Task (hours to 1 day)
- Technical work
- Refactoring, infrastructure
- No direct user impact

### Bug
- Defect in existing functionality
- Regression
- Error or crash

### Spike (research)
- Investigation needed
- Unknown scope
- POC required

## Output Format
```json
{
  "classification": "story|task|bug|epic|spike",
  "complexity": "XS|S|M|L|XL",
  "title": "refined title",
  "description": "detailed description",
  "acceptance_criteria": ["criterion 1", "criterion 2"],
  "subtasks": [
    {"title": "subtask 1", "type": "task", "complexity": "S"},
    {"title": "subtask 2", "type": "task", "complexity": "M"}
  ],
  "labels": ["frontend", "api", "database"],
  "components": ["auth", "payments"],
  "dependencies": ["PROJ-123", "PROJ-456"]
}
```

## Tools
- jira_search: Find related tickets
- github_search: Find related code
- knowledge_graph_search: Find affected components
```

#### 3.2 Task Classifier Skill (`.claude/skills/task-classification/SKILL.md`)

```markdown
# Task Classification Skill

## Purpose
Analyze and classify incoming task requests.

## Process

### 1. Analyze Request
- Parse natural language description
- Identify key requirements
- Detect technical vs business language

### 2. Research Context
- Search Jira for similar tickets
- Search codebase for related components
- Check knowledge graph for dependencies

### 3. Classify
Apply classification rules:
- Contains "error", "crash", "broken" → Bug
- Contains "as a user", "should be able to" → Story
- Contains "refactor", "upgrade", "migrate" → Task
- Contains "investigate", "research", "POC" → Spike
- Large scope, multiple features → Epic

### 4. Break Down (if needed)
For L/XL complexity:
- Identify logical chunks
- Create subtasks
- Map dependencies
- Estimate each subtask

### 5. Output
Generate structured ticket data for Jira creation.
```

---

## Phase 4: Product Agent (Week 7-8)

### Goal
Analyze application features and automatically generate development tasks/stories.

### New Agent Definition

#### 4.1 Product Agent (`.claude/agents/product-agent.md`)

```markdown
# Product Agent

## Role
Act as a Product Manager that analyzes the application and generates feature improvements, user stories, and development tasks.

## Capabilities
1. Analyze existing codebase and features
2. Identify improvement opportunities
3. Generate user stories with acceptance criteria
4. Prioritize based on impact and effort
5. Create comprehensive PRDs

## Analysis Modes

### 1. Feature Gap Analysis
- Compare with competitors
- Identify missing features
- Suggest enhancements

### 2. Technical Debt Analysis
- Find deprecated patterns
- Identify refactoring needs
- Security improvements

### 3. User Experience Analysis
- Analyze user flows
- Identify friction points
- Suggest UX improvements

### 4. Performance Analysis
- Identify slow endpoints
- Database optimization opportunities
- Caching opportunities

## Output Format
```json
{
  "analysis_type": "feature_gap|tech_debt|ux|performance",
  "findings": [
    {
      "title": "finding title",
      "description": "detailed description",
      "impact": "high|medium|low",
      "effort": "high|medium|low",
      "priority_score": 8.5,
      "suggested_tickets": [
        {
          "type": "story",
          "title": "ticket title",
          "description": "...",
          "acceptance_criteria": ["..."]
        }
      ]
    }
  ]
}
```

## Tools
- knowledge_graph_search: Understand codebase structure
- github_search: Find patterns and implementations
- jira_search: Check existing backlog
```

#### 4.2 Product Analysis Skill (`.claude/skills/product-analysis/SKILL.md`)

```markdown
# Product Analysis Skill

## Purpose
Analyze codebase and generate product improvement suggestions.

## Process

### 1. Codebase Analysis
```bash
# Analyze code structure
knowledge_graph_search("all entities")

# Find common patterns
grep -r "TODO|FIXME|HACK" src/

# Check test coverage
pytest --cov --cov-report=json
```

### 2. Feature Mapping
- List all routes/endpoints
- Map UI components to features
- Identify feature completeness

### 3. Gap Identification
- Missing error handling
- Incomplete features
- Missing tests
- Security gaps

### 4. Story Generation
For each gap:
1. Write user story format
2. Define acceptance criteria
3. Estimate complexity
4. Add technical notes

### 5. Prioritization
Score each suggestion:
- Business impact (1-10)
- Technical risk (1-10)
- Effort estimate (1-10)
- Priority = (impact * 2 - risk) / effort
```

---

## Phase 5: Self-Healing Loop Integration (Week 9-10)

### Goal
Connect all agents into a continuous self-improvement loop.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-HEALING ORCHESTRATOR                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ QA Agent │   │Log Monitor│   │ Product  │   │ Sentry   │    │
│  │          │   │          │   │  Agent   │   │ (exists) │    │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘    │
│       │              │              │              │           │
│       └──────────────┴──────────────┴──────────────┘           │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               TASK CLASSIFIER AGENT                      │   │
│  │     (Dedupe, classify, prioritize, create tickets)      │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    JIRA BACKLOG                          │   │
│  │          (Tickets with AI-Fix label)                    │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │ Webhook                            │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               EXISTING PIPELINE                          │   │
│  │  API Gateway → Brain → Planning → Executor → Verifier   │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    GITHUB PR                             │   │
│  │         (Created with fix implementation)               │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │ Human Approval / Auto-merge        │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    CI/CD PIPELINE                        │   │
│  │              (Build, test, deploy)                      │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               DEPLOYED APPLICATION                       │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│              ┌─────────────┴─────────────┐                     │
│              ▼                           ▼                      │
│         QA Agent                   Log Monitor                  │
│     (runs tests again)         (watches for errors)            │
│              │                           │                      │
│              └───────────LOOP────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Orchestrator Service

#### 5.1 Self-Healing Orchestrator (`orchestrator/`)

```python
# orchestrator/core/healing_loop.py
import asyncio
from datetime import datetime, timedelta

class SelfHealingOrchestrator:
    def __init__(self):
        self.qa_agent = QAAgentClient()
        self.log_monitor = LogMonitorClient()
        self.product_agent = ProductAgentClient()
        self.task_classifier = TaskClassifierClient()
        self.jira_client = JiraClient()
        self.metrics = MetricsCollector()

    async def run_healing_cycle(self):
        """Execute one complete self-healing cycle."""
        cycle_id = generate_cycle_id()
        logger.info("healing_cycle_started", cycle_id=cycle_id)

        # 1. Collect issues from all sources
        issues = await asyncio.gather(
            self.qa_agent.get_failures(),
            self.log_monitor.get_errors(),
            self.product_agent.get_suggestions(),
            return_exceptions=True
        )

        # 2. Flatten and deduplicate
        all_issues = self._deduplicate(self._flatten(issues))

        # 3. Classify each issue
        classified = await asyncio.gather(*[
            self.task_classifier.classify(issue)
            for issue in all_issues
        ])

        # 4. Create Jira tickets (will trigger existing pipeline)
        for item in classified:
            if not await self._ticket_exists(item):
                ticket = await self.jira_client.create_issue(
                    project="PROJ",
                    issuetype=item.classification,
                    summary=item.title,
                    description=item.description,
                    labels=["AI-Fix", "auto-generated", f"cycle-{cycle_id}"]
                )
                logger.info("ticket_created", ticket_key=ticket.key, cycle_id=cycle_id)

        # 5. Record metrics
        self.metrics.record_cycle(cycle_id, len(classified))

        return CycleResult(cycle_id=cycle_id, issues_processed=len(classified))

    async def run_forever(self, interval_hours: int = 6):
        """Run continuous self-healing loop."""
        while True:
            try:
                result = await self.run_healing_cycle()
                logger.info("healing_cycle_completed", **result.dict())
            except Exception as e:
                logger.error("healing_cycle_failed", error=str(e))

            await asyncio.sleep(interval_hours * 3600)
```

### Configuration

```yaml
# orchestrator/config.yaml
healing_loop:
  enabled: true
  interval_hours: 6

sources:
  qa_agent:
    enabled: true
    run_before_cycle: true
  log_monitor:
    enabled: true
    lookback_hours: 6
  product_agent:
    enabled: true
    run_weekly: true
  sentry:
    enabled: true

deduplication:
  similarity_threshold: 0.85
  lookback_days: 7

ticket_creation:
  auto_create: true
  require_approval_for:
    - epic
    - story
  auto_approve:
    - bug
    - task

auto_merge:
  enabled: false  # Start with human approval
  require_passing_ci: true
  require_qa_pass: true
```

---

## Phase 6: Dashboard Integration (Week 11-12)

### Goal
Visualize the self-healing system status and metrics.

### Dashboard Components

#### 6.1 New Dashboard Views

```typescript
// external-dashboard/src/components/SelfHealingDashboard.tsx

interface HealingCycle {
  id: string;
  startedAt: Date;
  completedAt: Date;
  issuesFound: number;
  ticketsCreated: number;
  prsOpened: number;
  prsMerged: number;
  status: 'running' | 'completed' | 'failed';
}

interface AgentStatus {
  name: string;
  status: 'active' | 'idle' | 'error';
  lastRun: Date;
  issuesFound: number;
}

export function SelfHealingDashboard() {
  return (
    <div className="grid grid-cols-3 gap-4">
      {/* Cycle Timeline */}
      <CycleTimeline cycles={cycles} />

      {/* Agent Status Cards */}
      <AgentStatusGrid agents={[
        { name: 'QA Agent', ... },
        { name: 'Log Monitor', ... },
        { name: 'Product Agent', ... },
        { name: 'Task Classifier', ... },
      ]} />

      {/* Metrics Charts */}
      <MetricsCharts data={{
        bugsDetected: [...],
        bugsFixed: [...],
        mttr: [...],  // Mean Time To Repair
        successRate: [...],
      }} />

      {/* Active Issues */}
      <ActiveIssuesList issues={activeIssues} />

      {/* Recent Fixes */}
      <RecentFixesList fixes={recentFixes} />
    </div>
  );
}
```

---

## Implementation Checklist

### Phase 1: Log Monitor (Week 1-2)
- [ ] Create `log-monitor/` service structure
- [ ] Implement Docker log collection
- [ ] Implement error pattern detection
- [ ] Implement AI error classification
- [ ] Implement Jira ticket creation
- [ ] Add deduplication (prevent spam)
- [ ] Write tests
- [ ] Add to docker-compose.yml
- [ ] Document in ARCHITECTURE.md

### Phase 2: QA Agent (Week 3-4)
- [ ] Create `qa-agent/` service structure
- [ ] Implement Playwright browser automation
- [ ] Create base flow framework
- [ ] Implement AI flow generation
- [ ] Implement failure analysis
- [ ] Implement bug report generation
- [ ] Write tests
- [ ] Add to docker-compose.yml

### Phase 3: Task Classifier (Week 5-6)
- [ ] Create task-classifier agent definition
- [ ] Create task-classification skill
- [ ] Implement classification logic
- [ ] Implement task breakdown logic
- [ ] Implement Jira integration
- [ ] Write tests
- [ ] Update brain agent to use classifier

### Phase 4: Product Agent (Week 7-8)
- [ ] Create product-agent definition
- [ ] Create product-analysis skill
- [ ] Implement codebase analysis
- [ ] Implement gap identification
- [ ] Implement story generation
- [ ] Implement prioritization
- [ ] Write tests

### Phase 5: Self-Healing Loop (Week 9-10)
- [ ] Create `orchestrator/` service
- [ ] Implement healing cycle
- [ ] Implement deduplication
- [ ] Implement source aggregation
- [ ] Add metrics collection
- [ ] Configure cycle timing
- [ ] Write tests
- [ ] Add to docker-compose.yml

### Phase 6: Dashboard (Week 11-12)
- [ ] Add healing cycle API endpoints
- [ ] Add agent status endpoints
- [ ] Create dashboard components
- [ ] Add metrics visualization
- [ ] Add real-time updates (WebSocket)
- [ ] Write tests

---

## Quick Start (Minimal MVP)

To get started immediately with the most impactful component:

### Step 1: Log Monitor MVP (3-5 days)

```bash
# Create the service
mkdir -p agent-bot/log-monitor/{core,workers,tests}

# Implement core functionality
# - Docker log collection
# - Simple regex error detection
# - Jira ticket creation
```

### Step 2: Test the Loop

```bash
# 1. Start the system
make cli-up PROVIDER=claude SCALE=1

# 2. Start log monitor
docker-compose up log-monitor

# 3. Trigger an error in your app
curl http://localhost:3000/api/trigger-error

# 4. Watch the magic:
#    - Log monitor detects error
#    - Creates Jira ticket with AI-Fix label
#    - Webhook triggers agent-bot
#    - Agent creates PR with fix
#    - PR ready for review
```

---

## Cost Estimate

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Log Monitor | ~$10-20 | Low token usage (classification only) |
| QA Agent | ~$50-100 | Higher usage (flow generation, analysis) |
| Task Classifier | ~$20-30 | Medium usage per ticket |
| Product Agent | ~$30-50 | Weekly analysis |
| **Total Additional** | **~$110-200/month** | On top of existing costs |

---

## Next Steps

1. **Start with Log Monitor** - Most immediate value, connects to existing pipeline
2. **Add QA Agent** - Proactive bug detection
3. **Add Task Classifier** - Improves ticket quality
4. **Add Product Agent** - Long-term improvements
5. **Build Orchestrator** - Ties everything together
6. **Enhance Dashboard** - Visibility and metrics

Would you like me to start implementing Phase 1 (Log Monitor)?
