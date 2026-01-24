# Architecture Documentation with Mermaid Diagrams

This document provides comprehensive visual documentation of the Claude Code Agent architecture using Mermaid diagrams. It covers system architecture, component relationships, data flows, file usage, and dependencies.

---

## 1. System Architecture Overview

The Claude Code Agent is a self-managing machine where FastAPI runs as a daemon and Claude Code CLI is spawned on-demand per request.

```mermaid
graph TB
    subgraph Container["Container (Pod)"]
        subgraph FastAPIServer["FastAPI Server (DAEMON)"]
            WebhooksAPI["Webhooks API<br/>/webhooks/github<br/>/webhooks/jira<br/>/webhooks/slack<br/>/webhooks/sentry"]
            DashboardAPI["Dashboard API<br/>/api/dashboard<br/>/api/conversations<br/>/api/analytics"]
            WebSocketAPI["WebSocket API<br/>/ws/{session_id}"]
            DynamicWebhooks["Dynamic Webhooks<br/>/webhooks/{provider}/{id}"]
        end
        
        subgraph TaskQueue["Task Queue (Redis)"]
            Queue["task_queue<br/>Redis List"]
        end
        
        subgraph TaskWorker["Task Worker (Python async)"]
            WorkerLoop["Worker Loop<br/>Concurrent Processing"]
            Semaphore["Semaphore<br/>Max Concurrent Tasks"]
        end
        
        subgraph ClaudeCLI["Claude Code CLI (ON-DEMAND)"]
            CLIBrain["Brain: /app/"]
            CLIAgents["Agents: .claude/agents/*.md"]
            CLISkills["Skills: .claude/skills/"]
        end
        
        subgraph DataStores["Data Stores"]
            SQLiteDB["SQLite Database<br/>Tasks, Conversations<br/>Sessions, Webhooks"]
            RedisCache["Redis Cache<br/>Queue, Output Buffer<br/>Session State"]
        end
    end
    
    subgraph ExternalServices["External Services"]
        GitHub["GitHub"]
        Jira["Jira"]
        Slack["Slack"]
        Sentry["Sentry"]
    end
    
    subgraph Dashboard["Dashboard v2 (React)"]
        Overview["Overview"]
        Analytics["Analytics"]
        Ledger["Ledger"]
        WebhooksUI["Webhooks"]
        Chat["Chat"]
        Registry["Registry"]
    end
    
    ExternalServices -->|Webhook Events| WebhooksAPI
    ExternalServices -->|Webhook Events| DynamicWebhooks
    Dashboard -->|HTTP API| DashboardAPI
    Dashboard -->|WebSocket| WebSocketAPI
    
    DashboardAPI -->|Create Task| Queue
    WebhooksAPI -->|Create Task| Queue
    DynamicWebhooks -->|Create Task| Queue
    
    Queue -->|Pop Task| WorkerLoop
    WorkerLoop -->|Spawn CLI| ClaudeCLI
    WorkerLoop -->|Stream Output| WebSocketAPI
    WorkerLoop -->|Save Results| SQLiteDB
    WorkerLoop -->|Buffer Output| RedisCache
    
    ClaudeCLI -->|Read Config| CLIBrain
    ClaudeCLI -->|Load Agents| CLIAgents
    ClaudeCLI -->|Load Skills| CLISkills
    
    DashboardAPI -->|Query Data| SQLiteDB
    DashboardAPI -->|Query Cache| RedisCache
    WebSocketAPI -->|Broadcast Events| Dashboard
```

---

## 2. Component Relationships

This diagram shows how different modules interact within the system.

```mermaid
graph LR
    subgraph EntryPoints["Entry Points"]
        MainPy["main.py<br/>FastAPI App"]
        TaskWorkerPy["workers/task_worker.py<br/>Task Processor"]
    end
    
    subgraph APILayer["API Layer"]
        DashboardAPI["api/dashboard.py"]
        ConversationsAPI["api/conversations.py"]
        WebhooksStatic["api/webhooks/<br/>github.py, jira.py<br/>slack.py, sentry.py"]
        WebhooksDynamic["api/webhooks_dynamic.py"]
        WebSocketAPI["api/websocket.py"]
        AnalyticsAPI["api/analytics.py"]
        RegistryAPI["api/registry.py"]
    end
    
    subgraph CoreLayer["Core Layer"]
        CLIRunner["core/cli_runner.py<br/>CLI Execution"]
        WebhookEngine["core/webhook_engine.py<br/>Command Execution"]
        WebhookConfigs["core/webhook_configs.py<br/>Static Configs"]
        WebSocketHub["core/websocket_hub.py<br/>WS Management"]
        DatabaseModels["core/database/models.py<br/>SQLAlchemy Models"]
        RedisClient["core/database/redis_client.py<br/>Redis Client"]
        ClaudeTasksSync["core/claude_tasks_sync.py<br/>Tasks Sync"]
    end
    
    subgraph SharedLayer["Shared Layer"]
        MachineModels["shared/machine_models.py<br/>Pydantic Models"]
    end
    
    subgraph Frontend["Frontend"]
        DashboardV2["services/dashboard-v2/<br/>React TypeScript"]
    end
    
    MainPy -->|Includes| APILayer
    MainPy -->|Starts| TaskWorkerPy
    
    APILayer -->|Uses| CoreLayer
    APILayer -->|Validates| MachineModels
    
    TaskWorkerPy -->|Executes| CLIRunner
    TaskWorkerPy -->|Uses| WebSocketHub
    TaskWorkerPy -->|Queries| DatabaseModels
    TaskWorkerPy -->|Pushes/Pops| RedisClient
    TaskWorkerPy -->|Syncs| ClaudeTasksSync
    
    WebhooksStatic -->|Uses| WebhookConfigs
    WebhooksDynamic -->|Uses| WebhookEngine
    WebhookEngine -->|Creates Tasks| DatabaseModels
    
    CLIRunner -->|Reads| WebhookConfigs
    
    CoreLayer -->|Validates| MachineModels
    
    Frontend -->|Calls| APILayer
    Frontend -->|Connects| WebSocketAPI
```

---

## 3. Data Flows

### 3.1 Dashboard Chat Flow

This sequence diagram shows the complete flow when a user sends a message through the dashboard.

```mermaid
sequenceDiagram
    participant User as User
    participant Dashboard as Dashboard v2
    participant ChatAPI as /api/chat
    participant DB as SQLite Database
    participant Queue as Redis Queue
    participant Worker as Task Worker
    participant CLI as Claude CLI
    participant WS as WebSocket Hub
    participant DashboardWS as Dashboard WebSocket

    User->>Dashboard: Send message
    Dashboard->>ChatAPI: POST /api/chat
    
    ChatAPI->>DB: Get/Create Session
    ChatAPI->>DB: Get/Create Conversation
    ChatAPI->>DB: Get last 20 messages (context)
    ChatAPI->>DB: Create TaskDB (QUEUED)
    ChatAPI->>DB: Create ConversationMessageDB (user)
    ChatAPI->>Queue: Push task_id
    
    ChatAPI-->>Dashboard: Return task_id, conversation_id
    
    Worker->>Queue: Pop task_id (blocking)
    Worker->>DB: Update TaskDB (RUNNING)
    Worker->>WS: Broadcast task.created
    
    Worker->>CLI: Spawn Claude CLI<br/>(with context + message)
    Worker->>WS: Stream output chunks
    
    WS->>DashboardWS: task.output events
    DashboardWS->>Dashboard: Update UI with stream
    
    CLI-->>Worker: Execution complete<br/>(success, cost, tokens)
    
    Worker->>DB: Update TaskDB (COMPLETED)<br/>(output, cost, tokens)
    Worker->>DB: Create ConversationMessageDB (assistant)
    Worker->>DB: Update Conversation (updated_at)
    Worker->>WS: Broadcast task.completed
    
    WS->>DashboardWS: task.completed event
    DashboardWS->>Dashboard: Show final response
    Dashboard->>User: Display message
```

### 3.2 Webhook Flow (Static Routes)

This sequence diagram shows the flow when a webhook is received via static routes (hard-coded handlers).

```mermaid
sequenceDiagram
    participant External as External Service<br/>(GitHub/Jira/Slack/Sentry)
    participant WebhookAPI as Static Webhook Handler<br/>(api/webhooks/*.py)
    participant WebhookConfigs as webhook_configs.py
    participant DB as SQLite Database
    participant Queue as Redis Queue
    participant Worker as Task Worker
    participant CLI as Claude CLI
    participant WS as WebSocket Hub
    participant SlackNotif as Slack Notification

    External->>WebhookAPI: POST /webhooks/{provider}
    
    WebhookAPI->>WebhookAPI: Verify signature
    WebhookAPI->>WebhookConfigs: Match command<br/>(by name/aliases + prefix)
    
    alt Command Matched
        WebhookAPI->>External: Send immediate response<br/>(reaction/ephemeral)
        WebhookAPI->>WebhookAPI: Render template<br/>({{variable}} syntax)
        WebhookAPI->>WebhookAPI: Wrap with brain instructions
        
        WebhookAPI->>DB: Create SessionDB (webhook-system)
        WebhookAPI->>DB: Create TaskDB (QUEUED)<br/>(with flow_id, external_id)
        WebhookAPI->>DB: Get/Create ConversationDB<br/>(by flow_id)
        WebhookAPI->>DB: Create ConversationMessageDB
        WebhookAPI->>DB: Sync to Claude Tasks<br/>(if enabled)
        WebhookAPI->>Queue: Push task_id
        
        WebhookAPI-->>External: 200 OK
        
        Worker->>Queue: Pop task_id
        Worker->>DB: Update TaskDB (RUNNING)
        Worker->>SlackNotif: Send job start notification
        
        Worker->>CLI: Spawn Claude CLI<br/>(in agent directory)
        Worker->>WS: Stream output
        
        CLI-->>Worker: Execution complete
        
        Worker->>DB: Update TaskDB (COMPLETED)
        Worker->>DB: Update ConversationMessageDB
        Worker->>SlackNotif: Send completion notification
        Worker->>WS: Broadcast task.completed
        
    else No Command Matched
        WebhookAPI-->>External: 200 OK (no action)
    end
```

### 3.3 Webhook Flow (Dynamic Routes)

This sequence diagram shows the flow when a webhook is received via dynamic routes (database-driven).

```mermaid
sequenceDiagram
    participant External as External Service
    participant DynamicAPI as Dynamic Webhook Handler<br/>(api/webhooks_dynamic.py)
    participant DB as SQLite Database
    participant WebhookEngine as webhook_engine.py
    participant Queue as Redis Queue
    participant Worker as Task Worker
    participant CLI as Claude CLI

    External->>DynamicAPI: POST /webhooks/{provider}/{webhook_id}
    
    DynamicAPI->>DB: Load WebhookConfigDB
    DynamicAPI->>DynamicAPI: Verify HMAC signature
    
    DynamicAPI->>DB: Query WebhookCommandDB<br/>(by trigger + conditions)
    DynamicAPI->>DB: Sort by priority
    
    loop For each matching command
        DynamicAPI->>WebhookEngine: Execute command action
        
        alt Action: create_task
            WebhookEngine->>WebhookEngine: Render template
            WebhookEngine->>WebhookEngine: Generate flow_id
            WebhookEngine->>DB: Create SessionDB
            WebhookEngine->>DB: Create TaskDB (QUEUED)
            WebhookEngine->>DB: Get/Create ConversationDB
            WebhookEngine->>DB: Create ConversationMessageDB
            WebhookEngine->>Queue: Push task_id
            
        else Action: comment
            WebhookEngine->>External: Post comment back
            
        else Action: github_reaction
            WebhookEngine->>External: Add reaction
            
        else Action: github_label
            WebhookEngine->>External: Add label
        end
    end
    
    DynamicAPI-->>External: 200 OK
    
    Worker->>Queue: Pop task_id
    Worker->>DB: Update TaskDB (RUNNING)
    Worker->>CLI: Spawn Claude CLI
    CLI-->>Worker: Execution complete
    Worker->>DB: Update TaskDB (COMPLETED)
```

### 3.4 Task Processing Flow

This sequence diagram shows the detailed task processing flow from queue to completion.

```mermaid
sequenceDiagram
    participant Queue as Redis Queue
    participant Worker as Task Worker
    participant Semaphore as Semaphore<br/>(Concurrency Limit)
    participant DB as SQLite Database
    participant RedisCache as Redis Cache
    participant CLI as Claude CLI
    participant WS as WebSocket Hub
    participant ClaudeTasks as Claude Tasks Dir<br/>(~/.claude/tasks/)

    Worker->>Queue: Pop task_id (blocking, timeout=5s)
    
    alt Task Available
        Worker->>Semaphore: Acquire (wait if at limit)
        Worker->>DB: Load TaskDB by task_id
        Worker->>DB: Update status = RUNNING
        Worker->>DB: Set started_at timestamp
        
        Worker->>DB: Load ConversationDB<br/>(get context: last 20 messages)
        
        Worker->>RedisCache: Initialize output buffer
        Worker->>WS: Broadcast task.created event
        
        Worker->>CLI: Spawn Claude CLI<br/>(prompt, working_dir, model, agents)
        
        par CLI Execution & Output Streaming
            CLI->>CLI: Execute Claude Code CLI
            CLI->>RedisCache: Stream output chunks
            Worker->>WS: Broadcast task.output events
        end
        
        CLI-->>Worker: CLIResult<br/>(success, output, cost, tokens)
        
        alt Success
            Worker->>DB: Update TaskDB<br/>(status=COMPLETED, output, cost, tokens)
            Worker->>DB: Create ConversationMessageDB<br/>(role=assistant)
            Worker->>DB: Update ConversationDB<br/>(updated_at, metrics)
            Worker->>ClaudeTasks: Update Claude task status<br/>(if synced)
            Worker->>WS: Broadcast task.completed
            
        else Failed
            Worker->>DB: Update TaskDB<br/>(status=FAILED, error)
            Worker->>ClaudeTasks: Update Claude task status (failed)
            Worker->>WS: Broadcast task.failed
        end
        
        Worker->>RedisCache: Cleanup output buffer
        Worker->>Semaphore: Release
        
    else No Task (timeout)
        Worker->>Worker: Sleep 1s, continue loop
    end
```

---

## 4. File Usage Map

This diagram shows which files are used by which components and features.

```mermaid
graph TB
    subgraph DashboardFeatures["Dashboard v2 Features"]
        OverviewFeature["Overview Feature"]
        AnalyticsFeature["Analytics Feature"]
        LedgerFeature["Ledger Feature"]
        WebhooksFeature["Webhooks Feature"]
        ChatFeature["Chat Feature"]
        RegistryFeature["Registry Feature"]
    end
    
    subgraph APIEndpoints["API Endpoints"]
        DashboardAPI["api/dashboard.py"]
        ConversationsAPI["api/conversations.py"]
        AnalyticsAPI["api/analytics.py"]
        WebhooksStaticAPI["api/webhooks/github.py<br/>api/webhooks/jira.py<br/>api/webhooks/slack.py<br/>api/webhooks/sentry.py"]
        WebhooksDynamicAPI["api/webhooks_dynamic.py"]
        WebSocketAPI["api/websocket.py"]
        RegistryAPI["api/registry.py"]
    end
    
    subgraph CoreModules["Core Modules"]
        CLIRunner["core/cli_runner.py"]
        WebhookEngine["core/webhook_engine.py"]
        WebhookConfigs["core/webhook_configs.py"]
        WebSocketHub["core/websocket_hub.py"]
        DatabaseModels["core/database/models.py"]
        RedisClient["core/database/redis_client.py"]
        ClaudeTasksSync["core/claude_tasks_sync.py"]
    end
    
    subgraph Workers["Workers"]
        TaskWorker["workers/task_worker.py"]
    end
    
    subgraph Shared["Shared"]
        MachineModels["shared/machine_models.py"]
    end
    
    subgraph Entry["Entry Points"]
        MainPy["main.py"]
    end
    
    OverviewFeature -->|GET /api/dashboard/status| DashboardAPI
    OverviewFeature -->|GET /api/tasks| DashboardAPI
    OverviewFeature -->|WebSocket| WebSocketAPI
    
    AnalyticsFeature -->|GET /api/analytics/*| AnalyticsAPI
    AnalyticsAPI -->|Queries| DatabaseModels
    
    LedgerFeature -->|GET /api/dashboard/tasks| DashboardAPI
    DashboardAPI -->|Queries| DatabaseModels
    
    WebhooksFeature -->|GET /api/webhooks| WebhooksDynamicAPI
    WebhooksFeature -->|POST /api/webhooks| WebhooksDynamicAPI
    WebhooksDynamicAPI -->|Uses| WebhookEngine
    WebhooksDynamicAPI -->|Queries| DatabaseModels
    
    ChatFeature -->|POST /api/chat| DashboardAPI
    ChatFeature -->|GET /api/conversations| ConversationsAPI
    ChatFeature -->|WebSocket| WebSocketAPI
    DashboardAPI -->|Creates Tasks| DatabaseModels
    ConversationsAPI -->|Manages| DatabaseModels
    
    RegistryFeature -->|GET /api/registry/*| RegistryAPI
    RegistryAPI -->|Reads/Writes| CoreModules
    
    WebhooksStaticAPI -->|Uses| WebhookConfigs
    WebhooksStaticAPI -->|Creates Tasks| DatabaseModels
    
    TaskWorker -->|Executes| CLIRunner
    TaskWorker -->|Uses| WebSocketHub
    TaskWorker -->|Queries| DatabaseModels
    TaskWorker -->|Pushes/Pops| RedisClient
    TaskWorker -->|Syncs| ClaudeTasksSync
    
    CLIRunner -->|Reads| WebhookConfigs
    
    WebhookEngine -->|Creates Tasks| DatabaseModels
    WebhookEngine -->|Uses| MachineModels
    
    MainPy -->|Includes| APIEndpoints
    MainPy -->|Starts| TaskWorker
    MainPy -->|Uses| CoreModules
    
    APIEndpoints -->|Validates| MachineModels
    CoreModules -->|Validates| MachineModels
    Workers -->|Uses| MachineModels
```

---

## 5. Component Dependencies

This diagram shows the dependency graph between modules, indicating which modules depend on others.

```mermaid
graph TD
    MainPy["main.py<br/>(Entry Point)"]
    TaskWorkerPy["workers/task_worker.py"]
    
    subgraph APIDeps["API Layer Dependencies"]
        DashboardAPI["api/dashboard.py"]
        ConversationsAPI["api/conversations.py"]
        WebhooksStatic["api/webhooks/*.py"]
        WebhooksDynamic["api/webhooks_dynamic.py"]
        WebSocketAPI["api/websocket.py"]
        AnalyticsAPI["api/analytics.py"]
        RegistryAPI["api/registry.py"]
    end
    
    subgraph CoreDeps["Core Layer Dependencies"]
        CLIRunner["core/cli_runner.py"]
        WebhookEngine["core/webhook_engine.py"]
        WebhookConfigs["core/webhook_configs.py"]
        WebSocketHub["core/websocket_hub.py"]
        DatabaseModels["core/database/models.py"]
        RedisClient["core/database/redis_client.py"]
        ClaudeTasksSync["core/claude_tasks_sync.py"]
        Config["core/config.py"]
    end
    
    subgraph SharedDeps["Shared Dependencies"]
        MachineModels["shared/machine_models.py"]
    end
    
    MainPy -->|Depends on| APIDeps
    MainPy -->|Depends on| CoreDeps
    MainPy -->|Starts| TaskWorkerPy
    
    TaskWorkerPy -->|Depends on| CLIRunner
    TaskWorkerPy -->|Depends on| WebSocketHub
    TaskWorkerPy -->|Depends on| DatabaseModels
    TaskWorkerPy -->|Depends on| RedisClient
    TaskWorkerPy -->|Depends on| ClaudeTasksSync
    TaskWorkerPy -->|Depends on| Config
    TaskWorkerPy -->|Depends on| MachineModels
    
    APIDeps -->|Depends on| CoreDeps
    APIDeps -->|Depends on| MachineModels
    
    WebhooksStatic -->|Depends on| WebhookConfigs
    WebhooksDynamic -->|Depends on| WebhookEngine
    WebSocketAPI -->|Depends on| WebSocketHub
    
    CoreDeps -->|Depends on| MachineModels
    CoreDeps -->|Depends on| Config
    
    WebhookEngine -->|Depends on| DatabaseModels
    WebhookEngine -->|Depends on| RedisClient
    WebhookEngine -->|Depends on| MachineModels
    
    CLIRunner -->|Depends on| Config
    
    DatabaseModels -->|Depends on| MachineModels
    RedisClient -->|Depends on| Config
    ClaudeTasksSync -->|Depends on| DatabaseModels
    ClaudeTasksSync -->|Depends on| Config
```

---

## 6. Key Files Reference

This table provides a quick reference for key files and their purposes.

| File Path | Purpose | Key Responsibilities |
|-----------|---------|---------------------|
| **Entry Points** |
| `main.py` | FastAPI application entry | Initialize app, register routers, start worker, handle lifespan |
| `workers/task_worker.py` | Task processing worker | Process tasks from queue, spawn CLI, stream output, update database |
| **API Layer** |
| `api/dashboard.py` | Dashboard API endpoints | Chat endpoint, task listing, status, agent listing |
| `api/conversations.py` | Conversation management | CRUD operations for conversations and messages |
| `api/webhooks/github.py` | GitHub webhook handler | Receive GitHub events, match commands, create tasks |
| `api/webhooks/jira.py` | Jira webhook handler | Receive Jira events, match commands, create tasks |
| `api/webhooks/slack.py` | Slack webhook handler | Receive Slack events, match commands, create tasks |
| `api/webhooks/sentry.py` | Sentry webhook handler | Receive Sentry events, match commands, create tasks |
| `api/webhooks_dynamic.py` | Dynamic webhook receiver | Handle database-driven webhooks, command matching |
| `api/websocket.py` | WebSocket endpoint | WebSocket connection handling, event broadcasting |
| `api/analytics.py` | Analytics API | Cost analytics, conversation analytics, usage patterns |
| `api/registry.py` | Registry API | Skills and agents CRUD operations |
| **Core Layer** |
| `core/cli_runner.py` | Claude CLI execution | Spawn Claude CLI process, capture output, calculate costs |
| `core/webhook_engine.py` | Webhook command execution | Execute webhook commands, render templates, create tasks |
| `core/webhook_configs.py` | Static webhook configs | Define hard-coded webhook configurations, validate at startup |
| `core/websocket_hub.py` | WebSocket hub | Manage WebSocket connections, broadcast events |
| `core/database/models.py` | Database models | SQLAlchemy ORM models (TaskDB, ConversationDB, etc.) |
| `core/database/redis_client.py` | Redis client | Redis connection, queue operations, output buffering |
| `core/claude_tasks_sync.py` | Claude Tasks sync | Sync orchestration tasks to ~/.claude/tasks/ directory |
| `core/config.py` | Configuration | Pydantic settings, environment variables, paths |
| **Shared Layer** |
| `shared/machine_models.py` | Domain models | Pydantic models with business rules (Task, Conversation, Session, etc.) |
| **Frontend** |
| `services/dashboard-v2/src/features/overview/` | Overview feature | System status, metrics, task monitoring |
| `services/dashboard-v2/src/features/analytics/` | Analytics feature | Cost analytics, conversation analytics |
| `services/dashboard-v2/src/features/ledger/` | Ledger feature | Transaction history, cost tracking |
| `services/dashboard-v2/src/features/webhooks/` | Webhooks feature | Webhook management UI |
| `services/dashboard-v2/src/features/chat/` | Chat feature | Conversation interface, message history |
| `services/dashboard-v2/src/features/registry/` | Registry feature | Skills and agents management |

---

## 7. Data Flow Summary

### Task Lifecycle States

```mermaid
stateDiagram-v2
    [*] --> QUEUED: Task Created
    QUEUED --> RUNNING: Worker Picks Up
    RUNNING --> COMPLETED: Success
    RUNNING --> FAILED: Error
    RUNNING --> CANCELLED: User Cancels
    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

### Conversation Flow Tracking

```mermaid
flowchart TD
    Start[External Event] --> GenerateFlowID[Generate flow_id from external_id]
    GenerateFlowID --> CreateRootTask[Create Root Task with flow_id]
    CreateRootTask --> GetOrCreateConv[Get or Create Conversation by flow_id]
    GetOrCreateConv --> QueueTask[Queue Task]
    QueueTask --> ProcessTask[Worker Processes Task]
    ProcessTask --> CreateChildTask{Task Creates<br/>Child Task?}
    CreateChildTask -->|Yes| InheritConv[Child Inherits conversation_id]
    InheritConv --> QueueTask
    CreateChildTask -->|No| UpdateMetrics[Update Conversation Metrics]
    UpdateMetrics --> Complete[Task Complete]
```

---

## 8. Storage Architecture

### SQLite Database Schema (Key Tables)

```mermaid
erDiagram
    TaskDB ||--o{ ConversationMessageDB : "linked_to"
    ConversationDB ||--o{ ConversationMessageDB : "contains"
    SessionDB ||--o{ TaskDB : "has"
    WebhookConfigDB ||--o{ WebhookCommandDB : "has"
    
    TaskDB {
        string task_id PK
        string session_id FK
        string conversation_id FK
        string flow_id
        string assigned_agent
        string status
        string input_message
        string output_stream
        float cost_usd
        int input_tokens
        int output_tokens
    }
    
    ConversationDB {
        string conversation_id PK
        string user_id
        string title
        datetime updated_at
    }
    
    ConversationMessageDB {
        string message_id PK
        string conversation_id FK
        string task_id FK
        string role
        string content
    }
    
    SessionDB {
        string session_id PK
        string user_id
        string machine_id
        float total_cost_usd
        int total_tasks
    }
    
    WebhookConfigDB {
        string webhook_id PK
        string provider
        string endpoint
        boolean enabled
    }
    
    WebhookCommandDB {
        string command_id PK
        string webhook_id FK
        string trigger
        string action
        string template
        int priority
    }
```

### Redis Usage

```mermaid
graph LR
    subgraph RedisUsage["Redis Usage"]
        TaskQueue["task_queue<br/>List<br/>Task IDs"]
        OutputBuffer["task:{id}:output<br/>String<br/>Output chunks"]
        SessionTasks["session:{id}:tasks<br/>Set<br/>Active task IDs"]
    end
    
    TaskQueue -->|Push/Pop| TaskWorker
    OutputBuffer -->|Append/Read| TaskWorker
    SessionTasks -->|Add/Remove| TaskWorker
```

---

## 9. Agent System Architecture

### Agent Directory Structure

```mermaid
graph TD
    subgraph ClaudeDir[".claude/"]
        BrainMD["agents/brain.md<br/>Main Orchestrator"]
        PlanningMD["agents/planning.md<br/>Analysis Agent"]
        ExecutorMD["agents/executor.md<br/>Implementation Agent"]
        ServiceIntegratorMD["agents/service-integrator.md<br/>Service Integration"]
        OtherAgents["agents/*.md<br/>Other Agents"]
        
        SkillsDir["skills/"]
        WebhookSkill["skills/webhook-management/"]
        TestingSkill["skills/testing/"]
        GitHubSkill["skills/github-operations/"]
        OtherSkills["skills/*/"]
    end
    
    BrainMD -->|Delegates to| PlanningMD
    BrainMD -->|Delegates to| ExecutorMD
    BrainMD -->|Delegates to| ServiceIntegratorMD
    BrainMD -->|Uses| WebhookSkill
    
    PlanningMD -->|Read-only tools| OtherSkills
    ExecutorMD -->|Uses| TestingSkill
    ServiceIntegratorMD -->|Uses| GitHubSkill
```

---

## Notes

- **Concurrency**: Task Worker uses a semaphore to limit concurrent tasks (default: 5)
- **Persistence**: SQLite for persistent data, Redis for ephemeral queue/cache
- **Real-time**: WebSocket for live updates, Redis for output buffering
- **Flow Tracking**: `flow_id` tracks end-to-end flows, `conversation_id` groups related tasks
- **Claude Tasks Sync**: Optional sync to `~/.claude/tasks/` for background agent visibility
- **Hybrid Webhooks**: Static routes (hard-coded) + Dynamic routes (database-driven)
- **Type Safety**: Pydantic models enforce business rules at the domain layer
