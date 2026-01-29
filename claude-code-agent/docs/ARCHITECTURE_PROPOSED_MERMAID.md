# Proposed Architecture - Detailed Mermaid Diagrams

Detailed architecture diagram according to requirements from todo.txt (lines 6-38)

---

## 1. Overview

```mermaid
graph TB
    subgraph Services["External Services"]
        GitHub["GitHub"]
        Jira["Jira"]
        Slack["Slack"]
        Sentry["Sentry"]
    end

    subgraph Gateway["API Gateway"]
        WebhookAPI["Webhook API<br/>/webhooks/*"]
    end

    subgraph ServicesContainer["Services Container (External)"]
        ServicesAPIDesc["Services API<br/>/api/services/*<br/>API or MCP<br/>GitHub/Jira/Slack/Sentry"]
    end

    subgraph Queue["Task Queue"]
        TaskQueue["Task Queue<br/>Redis<br/>Webhook → Agent Bridge"]
    end

    subgraph Agent["Agent Container"]
        AgentDesc["Task Execution<br/>Internal Management<br/>Internal Dashboard<br/>Skills & Agents"]
    end

    subgraph KnowledgeGraph["Knowledge Graph API (External)"]
        KGDesc["Knowledge Graph API<br/>Receives Webhooks<br/>Entity Relationships<br/>Context Storage"]
    end

    subgraph External["External Container"]
        ExternalDesc["Statistics<br/>Logs<br/>Webhook Management"]
    end

    subgraph Root["Root Directory"]
        RootDesc["claude.md<br/>docker-compose.yml<br/>Central Configuration"]
    end

    Services -->|Webhooks| WebhookAPI
    Services -->|API Calls| ServicesContainer
    ServicesContainer -->|GitHub API| GitHub
    ServicesContainer -->|Jira API| Jira
    ServicesContainer -->|Slack API| Slack
    ServicesContainer -->|Sentry API| Sentry

    WebhookAPI -->|Enqueue Tasks| TaskQueue
    TaskQueue -->|Dequeue Tasks| Agent
    WebhookAPI -->|Store| External
    ServicesContainer -->|Call| Agent
    ServicesContainer -->|Data| External

    Agent -->|Logs/Metrics| External
    Agent -->|Queries| KnowledgeGraph
    Agent -->|Uses| ServicesContainer
    WebhookAPI -->|Webhook Events| KnowledgeGraph

    Root -.->|Configures| Gateway
    Root -.->|Configures| Agent
    Root -.->|Configures| External
    Root -.->|Configures| KnowledgeGraph
    Root -.->|Configures| ServicesContainer

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Services,GitHub,Jira,Slack,Sentry,Gateway,WebhookAPI,ServicesContainer,ServicesAPIDesc,Queue,TaskQueue,Agent,AgentDesc,KnowledgeGraph,KGDesc,External,ExternalDesc,Root,RootDesc defaultNode
```

---

## 2. Agent Container (Full Details)

```mermaid
graph TB
    subgraph AgentContainer["Agent Container"]

        subgraph AgentDashboard["Internal Dashboard"]
            direction TB
            AgentMgmt["Agents Management"]
            SkillsMgmt["Skills Management"]
            RulesMgmt["Rules Management"]
            ChatUI["Chat Interface"]
            TaskLogsUI["Task Logs Viewer"]
        end

        subgraph AgentCore["Agent Core"]
            direction TB
            Engine["Agent Engine<br/>Task Execution"]
            Queue["Task Queue<br/>Redis"]
            Worker["Task Worker<br/>Task Processing"]
            CLIExec["CLI Executor<br/>Claude CLI Execution"]
        end

        subgraph AgentConfig["Configuration"]
            direction LR
            Rules["Rules<br/>.claude/rules/"]
            Skills["Skills<br/>.claude/skills/<br/>github-operations<br/>jira-operations<br/>slack-operations<br/>webhook-management<br/>testing<br/>verification"]
            Agents["Agents<br/>.claude/agents/<br/>planning<br/>executor<br/>verifier<br/>github-issue-handler<br/>github-pr-review<br/>jira-code-plan"]
            Commands["Commands<br/>.claude/commands/"]
            Hooks["Hooks<br/>.claude/hooks/"]
        end

        subgraph AgentFiles["Files"]
            direction TB
            Dockerfile["Dockerfile"]
            ClaudeMD["claude.md<br/>rules, skills, agent,<br/>commands, hooks"]
            MainPy["main.py"]
            Requirements["requirements.txt"]
        end

        subgraph AgentStorage["Local Storage"]
            direction TB
            LocalDB["Local Database"]
            LocalLogs["Local Logs"]
            TmpRepos["tmp/<br/>Relevant Repositories<br/>Cloned for Tasks"]
        end

        subgraph AgentExternalAccess["External Service Access"]
            direction TB
            MCPServer["MCP Server<br/>Model Context Protocol<br/>Service Integration"]
            ExternalService["External Service<br/>API Keys Manager<br/>GitHub/Jira/Slack APIs"]
        end
    end

    AgentDashboard -->|Manages| AgentMgmt
    AgentDashboard -->|Manages| SkillsMgmt
    AgentDashboard -->|Manages| RulesMgmt
    AgentDashboard -->|Interacts| ChatUI
    AgentDashboard -->|Views| TaskLogsUI

    Engine -->|Reads| ClaudeMD
    Engine -->|Loads| Rules
    Engine -->|Loads| Skills
    Engine -->|Loads| Agents
    Engine -->|Loads| Commands
    Engine -->|Loads| Hooks

    Engine -->|Creates Tasks| Queue
    Queue -->|Processes| Worker
    Worker -->|Executes| CLIExec
    Worker -->|Streams| TaskLogsUI
    Worker -->|Updates| LocalDB
    Worker -->|Writes| LocalLogs
    Worker -->|Clones Repos| TmpRepos

    Engine -->|Loads| Skills
    Engine -->|Loads| Agents
    Engine -->|Uses| MCPServer
    MCPServer -->|Connects| ExternalService
    Worker -->|Accesses| ExternalService
    ExternalService -->|GitHub API| GitHub
    ExternalService -->|Jira API| Jira
    ExternalService -->|Slack API| Slack

    ClaudeMD -.->|Configures| Engine
    Dockerfile -.->|Builds| AgentContainer
    MainPy -.->|Implements| Engine

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class AgentContainer,AgentDashboard,AgentMgmt,SkillsMgmt,RulesMgmt,ChatUI,TaskLogsUI,AgentCore,Engine,Queue,Worker,CLIExec,AgentConfig,Rules,Skills,Agents,Commands,Hooks,AgentFiles,Dockerfile,ClaudeMD,MainPy,Requirements,AgentStorage,LocalDB,LocalLogs,TmpRepos,AgentExternalAccess,MCPServer,ExternalService defaultNode
```

```mermaid
graph TB
    subgraph AgentContainer["Agent Container"]
        AgentEngine["Agent Engine"]
        Worker["Task Worker"]
    end

    subgraph WebhookAPI["Webhook API"]
        WebhookReceiver["Webhook Receiver<br/>/webhooks/*"]
    end

    subgraph KnowledgeGraph["Knowledge Graph API (External)"]
        direction TB
        KGAPI["Knowledge Graph API<br/>External Service"]
        KGEngine["Knowledge Graph Engine<br/>Entity Relationships<br/>Context Storage"]
        KGStorage["Knowledge Graph Storage<br/>Entities, Relationships"]
    end

    subgraph ExternalServices["External Services"]
        GitHub["GitHub"]
        Jira["Jira"]
        Slack["Slack"]
    end

    GitHub -->|Webhooks| WebhookReceiver
    Jira -->|Webhooks| WebhookReceiver
    Slack -->|Webhooks| WebhookReceiver

    WebhookReceiver -->|Webhook Events| KGAPI
    KGAPI -->|Processes| KGEngine
    KGEngine -->|Stores| KGStorage

    AgentEngine -->|Queries| KGAPI
    Worker -->|Queries| KGAPI
    Worker -->|Updates| KGAPI

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class AgentContainer,AgentEngine,Worker,WebhookAPI,WebhookReceiver,KnowledgeGraph,KGAPI,KGEngine,KGStorage,ExternalServices,GitHub,Jira,Slack defaultNode
```

---

## 3. External Container (Full Details)

```mermaid
graph TB
    subgraph ExternalContainer["External Container"]

        subgraph ExternalDashboard["External Dashboard"]
            direction TB
            StatsUI["Statistics<br/>Costs, Tasks, Performance"]
            LogsViewer["Logs Viewer<br/>Historical + Real-time"]
            WebhookMgmt["Webhook Management<br/>Create, Edit, Delete"]
            CommandsMgmt["Commands Management<br/>Command Configuration"]
            TriggersMgmt["Triggers Management<br/>Model Identification"]
        end

        subgraph ExternalAPI["External API"]
            direction TB
            DataAPI["Data API<br/>/api/data/*<br/>All Application Data"]
            CostsAPI["Costs API<br/>/api/costs<br/>Costs"]
            LogsAPI["Logs API<br/>/api/logs<br/>Logs"]
            ChatAPI["Chat Management API<br/>/api/chat<br/>Chat Management"]
            AnalyticsAPI["Analytics API<br/>/api/analytics<br/>Analytics"]
        end

        subgraph ExternalStorage["External Storage"]
            direction TB
            CentralDB["Centralized Database<br/>Tasks, Logs, Costs"]
            LogStorage["Log Storage<br/>Historical, Indexes"]
        end
    end

    ExternalDashboard -->|Queries| ExternalAPI
    ExternalDashboard -->|Manages| WebhookMgmt
    ExternalDashboard -->|Manages| CommandsMgmt
    ExternalDashboard -->|Manages| TriggersMgmt

    ExternalAPI -->|Reads/Writes| CentralDB
    ExternalAPI -->|Reads/Writes| LogStorage

    StatsUI -->|Queries| CostsAPI
    LogsViewer -->|Queries| LogsAPI

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class ExternalContainer,ExternalDashboard,StatsUI,LogsViewer,WebhookMgmt,CommandsMgmt,TriggersMgmt,ExternalAPI,DataAPI,CostsAPI,LogsAPI,ChatAPI,AnalyticsAPI,ExternalStorage,CentralDB,LogStorage defaultNode
```

---

## 4. API Gateway - Central Entry Point

```mermaid
graph TB
    subgraph Services["External Services"]
        GitHub["GitHub"]
        Jira["Jira"]
        Slack["Slack"]
        Sentry["Sentry"]
    end

    subgraph APIGateway["API Gateway"]
        subgraph WebhookAPI["Webhook API"]
            direction TB
            Receiver["Webhook Receiver<br/>/webhooks/*<br/>Event Reception"]
            Validator["Webhook Validator<br/>Signature Validation<br/>Routing"]
            Router["Webhook Router<br/>Route to Queue<br/>Load Balancing"]
        end

        subgraph TaskQueue["Task Queue"]
            Queue["Task Queue<br/>Redis<br/>Webhook → Agent Bridge"]
        end
    end

    subgraph ServicesContainer["Services Container (External)"]
        direction TB
        ServicesAPI["Services API<br/>/api/services/*"]
        MCP["MCP Server<br/>Model Context Protocol<br/>Future Support"]
        APIKeyManager["API Keys Manager<br/>GitHub/Jira/Slack/Sentry"]
        ServiceProxy["Service Proxy<br/>Unified API Access"]
    end

    subgraph Agent["Agent Container"]
        AgentContainer["Agent Container"]
    end

    subgraph External["External Container"]
        ExternalContainer["External Container"]
    end

    subgraph KnowledgeGraph["Knowledge Graph API (External)"]
        KGAPI["Knowledge Graph API<br/>External Service"]
    end

    Services -->|Webhook Events| Receiver
    Services -->|API Calls| ServicesAPI

    Receiver -->|Validates| Validator
    Validator -->|Routes| Router
    Router -->|Enqueues Tasks| Queue
    Router -->|Webhook Events| KGAPI
    Queue -->|Dequeues Tasks| AgentContainer
    Router -->|Stores Events| ExternalContainer

    ServicesAPI -->|Service Calls| AgentContainer
    ServicesAPI -->|Service Data| ExternalContainer
    ServicesAPI -->|Uses| ServiceProxy
    ServiceProxy -->|Uses| APIKeyManager
    ServiceProxy -->|GitHub API| GitHub
    ServiceProxy -->|Jira API| Jira
    ServiceProxy -->|Slack API| Slack
    ServiceProxy -->|Sentry API| Sentry

    MCP -->|Future: Direct Access| GitHub
    MCP -->|Future: Direct Access| Jira
    MCP -->|Future: Direct Access| Slack
    MCP -->|Future: Direct Access| Sentry

    AgentContainer -->|Queries| KGAPI
    AgentContainer -->|Uses| ServicesAPI
    AgentContainer -->|Uses| MCP

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Services,GitHub,Jira,Slack,Sentry,APIGateway,WebhookAPI,Receiver,Validator,Router,TaskQueue,Queue,ServicesContainer,ServicesAPI,MCP,APIKeyManager,ServiceProxy,Agent,AgentContainer,External,ExternalContainer,KnowledgeGraph,KGAPI defaultNode
```

---

## 5. Data Flow

### 5.1 Webhook Event Flow

```mermaid
sequenceDiagram
    autonumber
    participant ExtService as External Service
    participant WebhookAPI as Webhook API
    participant Queue as Task Queue
    participant KGAPI as Knowledge Graph API
    participant Agent as Agent Container
    participant External as External Container
    participant User as User

    Note over ExtService,User: Webhook Event Flow
    ExtService->>WebhookAPI: 1. Webhook Event
    WebhookAPI->>WebhookAPI: 2. Validate Signature
    WebhookAPI->>Queue: 3. Enqueue Task
    WebhookAPI->>KGAPI: 4. Forward Webhook Event
    KGAPI->>KGAPI: 5. Process & Store
    Queue->>Agent: 6. Dequeue Task
    Agent->>Agent: 7. Process Task
    Agent->>KGAPI: 8. Query Knowledge Graph
    KGAPI->>Agent: 9. Return Context
    Agent->>External: 10. Send Logs
    Agent->>External: 11. Send Metrics
    Agent->>External: 12. Send Costs
    External->>External: 13. Store in Database
    External->>User: 14. Display in Dashboard
```

### 5.2 Statistics Viewing Flow

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant ExternalDashboard as External Dashboard
    participant ExternalAPI as External API
    participant Database as Database

    Note over User,Database: Statistics Viewing Flow
    User->>ExternalDashboard: 1. Request Statistics
    ExternalDashboard->>ExternalAPI: 2. Query Costs API
    ExternalAPI->>Database: 3. Query Costs Data
    Database->>ExternalAPI: 4. Return Data
    ExternalAPI->>ExternalDashboard: 5. Return Results
    ExternalDashboard->>User: 6. Display Statistics
```

### 5.3 Chat with Agent Flow

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant AgentDashboard as Agent Dashboard
    participant AgentEngine as Agent Engine
    participant CLI as Claude CLI
    participant ServicesContainer as Services Container
    participant ExternalServices as GitHub/Jira/Slack
    participant External as External Container

    Note over User,External: Chat with Agent Flow
    User->>AgentDashboard: 1. Send Chat Message
    AgentDashboard->>AgentEngine: 2. Process Chat
    AgentEngine->>CLI: 3. Execute Claude CLI
    CLI->>AgentEngine: 4. Return Response
    AgentEngine->>ServicesContainer: 5. Request External Service (if needed)
    ServicesContainer->>ExternalServices: 6. Call Service API
    ExternalServices->>ServicesContainer: 7. Return Data
    ServicesContainer->>AgentEngine: 8. Return Service Data
    AgentEngine->>AgentDashboard: 9. Stream Response
    AgentDashboard->>User: 10. Display Response
    AgentEngine->>External: 11. Log Chat Interaction
```

### 5.4 Webhook Management Flow

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant ExternalDashboard as External Dashboard
    participant ExternalAPI as External API
    participant Database as Database
    participant WebhookAPI as Webhook API

    Note over User,WebhookAPI: Webhook Management Flow
    User->>ExternalDashboard: 1. Create/Edit Webhook
    ExternalDashboard->>ExternalAPI: 2. Update Webhook Config
    ExternalAPI->>Database: 3. Save Configuration
    Database->>ExternalAPI: 4. Confirm Save
    ExternalAPI->>WebhookAPI: 5. Update Routes
    WebhookAPI->>ExternalAPI: 6. Confirm Update
    ExternalAPI->>ExternalDashboard: 7. Success Response
    ExternalDashboard->>User: 8. Show Success Message
```

---

## 6. File Structure

```mermaid
graph TD
    Root["Root Directory<br/>/"]

    RootClaude["claude.md<br/>rules, commands, skills,<br/>agents, hooks, webhooks"]
    RootDocker["docker-compose.yml<br/>Container Orchestration"]
    RootEnv[".env<br/>Environment Variables"]
    RootMakefile["Makefile<br/>Management Commands"]

    AgentDir["agent-container/<br/>Agent Container Directory"]
    AgentDockerfile["Dockerfile<br/>Container Build"]
    AgentClaude["claude.md<br/>rules, skills, agent,<br/>commands, hooks"]
    AgentMain["main.py<br/>Entry Point"]
    AgentRequirements["requirements.txt<br/>Python Dependencies"]
    AgentConfig["config/<br/>Configuration Files"]
    AgentClaudeDir[".claude/<br/>Configuration Directory"]
    AgentRules[".claude/rules/<br/>Execution Rules"]
    AgentSkills[".claude/skills/<br/>Skills"]
    AgentAgents[".claude/agents/<br/>Agent Definitions"]

    ExternalDir["external-container/<br/>External Container Directory"]
    ExternalDockerfile["Dockerfile<br/>Container Build"]
    ExternalClaude["claude.md<br/>Configuration"]
    ExternalMain["main.py<br/>Entry Point"]
    ExternalDashboard["dashboard/<br/>React Dashboard"]
    ExternalAPI["api/<br/>API endpoints"]

    Root --> RootClaude
    Root --> RootDocker
    Root --> RootEnv
    Root --> RootMakefile
    Root --> AgentDir
    Root --> ExternalDir

    AgentDir --> AgentDockerfile
    AgentDir --> AgentClaude
    AgentDir --> AgentMain
    AgentDir --> AgentRequirements
    AgentDir --> AgentConfig
    AgentDir --> AgentClaudeDir
    AgentClaudeDir --> AgentRules
    AgentClaudeDir --> AgentSkills
    AgentClaudeDir --> AgentAgents
    AgentDir --> AgentTmp["tmp/<br/>Relevant Repositories"]

    ExternalDir --> ExternalDockerfile
    ExternalDir --> ExternalClaude
    ExternalDir --> ExternalMain
    ExternalDir --> ExternalDashboard
    ExternalDir --> ExternalAPI

    ServicesDir["services-container/<br/>Services Container<br/>External to API Gateway"]
    ServicesDockerfile["Dockerfile<br/>Services Container Build"]
    ServicesMain["main.py<br/>Services API Entry Point"]
    ServicesAPI["api/<br/>Services API endpoints"]
    ServicesMCP["mcp/<br/>MCP Server<br/>Future Support"]
    ServicesConfig["config/<br/>API Keys Configuration"]

    KGDir["knowledge-graph/<br/>Knowledge Graph Service<br/>External to Agent"]
    KGDockerfile["Dockerfile<br/>Knowledge Graph Build"]
    KGMain["main.py<br/>Knowledge Graph Engine"]
    KGStorage["storage/<br/>Knowledge Graph Storage"]

    Root --> ServicesDir
    Root --> KGDir
    ServicesDir --> ServicesDockerfile
    ServicesDir --> ServicesMain
    ServicesDir --> ServicesAPI
    ServicesDir --> ServicesMCP
    ServicesDir --> ServicesConfig
    KGDir --> KGDockerfile
    KGDir --> KGMain
    KGDir --> KGStorage

    RootClaude -.->|Defines| AgentClaude
    RootClaude -.->|Defines| ExternalClaude
    RootClaude -.->|Defines| ServicesDir

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Root,RootClaude,RootDocker,RootEnv,RootMakefile,AgentDir,AgentDockerfile,AgentClaude,AgentMain,AgentRequirements,AgentConfig,AgentClaudeDir,AgentRules,AgentSkills,AgentAgents,AgentTmp,ExternalDir,ExternalDockerfile,ExternalClaude,ExternalMain,ExternalDashboard,ExternalAPI,ServicesDir,ServicesDockerfile,ServicesMain,ServicesAPI,ServicesMCP,ServicesConfig,KGDir,KGDockerfile,KGMain,KGStorage defaultNode
```

---

## 7. Scaling Architecture

```mermaid
graph TB
    subgraph Incoming["Incoming Requests"]
        Requests["Requests<br/>Webhooks, API Calls"]
    end

    subgraph LoadBalancer["Load Balancer"]
        LB["Load Balancer<br/>Routes requests<br/>Distributes load"]
    end

    subgraph AgentInstances["Agent Container Instances"]
        direction TB
        Agent1["Agent Container 1<br/>- Dashboard<br/>- Engine<br/>- Tasks<br/>- Local Storage"]
        Agent2["Agent Container 2<br/>- Dashboard<br/>- Engine<br/>- Tasks<br/>- Local Storage"]
        Agent3["Agent Container N<br/>- Dashboard<br/>- Engine<br/>- Tasks<br/>- Local Storage"]
    end

    subgraph ExternalInstance["External Container Instance"]
        External["External Container<br/>- Statistics Dashboard<br/>- Logs Viewer<br/>- Webhook Management<br/>- Single Instance"]
    end

    subgraph SharedStorage["Shared Storage"]
        direction TB
        SharedDB["Shared Database<br/>- Tasks<br/>- Logs<br/>- Metrics<br/>- Costs"]
        SharedQueue["Shared Queue<br/>Redis<br/>Webhook → Agent Bridge<br/>Task Distribution"]
    end

    Requests -->|Routes| LB
    LB -->|Distributes| Agent1
    LB -->|Distributes| Agent2
    LB -->|Distributes| Agent3

    Agent1 -->|Read/Write| SharedDB
    Agent2 -->|Read/Write| SharedDB
    Agent3 -->|Read/Write| SharedDB

    Agent1 -->|Push Tasks| SharedQueue
    Agent2 -->|Push Tasks| SharedQueue
    Agent3 -->|Push Tasks| SharedQueue
    SharedQueue -->|Pop Tasks| Agent1
    SharedQueue -->|Pop Tasks| Agent2
    SharedQueue -->|Pop Tasks| Agent3

    Agent1 -->|Send Logs/Metrics| External
    Agent2 -->|Send Logs/Metrics| External
    Agent3 -->|Send Logs/Metrics| External

    External -->|Query| SharedDB

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Incoming,Requests,LoadBalancer,LB,AgentInstances,Agent1,Agent2,Agent3,ExternalInstance,External,SharedStorage,SharedDB,SharedQueue defaultNode
```

---

## 8. Services Container (External) - Detailed Architecture

```mermaid
graph TB
    subgraph AgentContainer["Agent Container"]
        AgentEngine["Agent Engine"]
        Worker["Task Worker"]
    end

    subgraph ExternalServices["External Services"]
        GitHub["GitHub"]
        Jira["Jira"]
        Slack["Slack"]
        Sentry["Sentry"]
    end

    subgraph ServicesContainer["Services Container (External)"]
        direction TB

        subgraph ServicesAPI["Services API"]
            APIEndpoint["API Endpoint<br/>/api/services/*<br/>REST API"]
            ServiceRegistry["Service Registry<br/>Service Registration<br/>Discovery, Health Checks"]
        end

        subgraph MCPServer["MCP Server"]
            MCP["Model Context Protocol<br/>Service Integration<br/>Tool Discovery<br/>Future Support"]
            MCPTools["MCP Tools<br/>GitHub Operations<br/>Jira Operations<br/>Slack Operations<br/>Sentry Operations"]
        end

        subgraph ServiceManagement["Service Management"]
            APIKeyManager["API Keys Manager<br/>Secure Storage<br/>GitHub/Jira/Slack/Sentry"]
            ServiceProxy["Service Proxy<br/>Unified API Access"]
        end
    end

    subgraph WebhookAPI["Webhook API"]
        WebhookReceiver["Webhook Receiver<br/>/webhooks/*"]
    end

    subgraph KnowledgeGraph["Knowledge Graph API (External)"]
        direction TB
        KGAPI["Knowledge Graph API<br/>External Service"]
        KGEngine["Knowledge Graph Engine<br/>Entity Relationships<br/>Context Storage"]
    end

    GitHub -->|Webhooks| WebhookReceiver
    Jira -->|Webhooks| WebhookReceiver
    Slack -->|Webhooks| WebhookReceiver
    Sentry -->|Webhooks| WebhookReceiver

    GitHub -->|API Calls| APIEndpoint
    Jira -->|API Calls| APIEndpoint
    Slack -->|API Calls| APIEndpoint
    Sentry -->|API Calls| APIEndpoint

    WebhookReceiver -->|Webhook Events| KGAPI
    KGAPI -->|Processes| KGEngine

    AgentEngine -->|Uses| APIEndpoint
    Worker -->|Uses| APIEndpoint
    AgentEngine -->|Uses| MCP
    Worker -->|Uses| MCP
    AgentEngine -->|Queries| KGAPI
    Worker -->|Queries| KGAPI
    Worker -->|Updates| KGAPI

    APIEndpoint -->|Uses| ServiceProxy
    ServiceProxy -->|Uses| APIKeyManager
    ServiceProxy -->|GitHub API| GitHub
    ServiceProxy -->|Jira API| Jira
    ServiceProxy -->|Slack API| Slack
    ServiceProxy -->|Sentry API| Sentry

    MCP -->|Discovers| MCPTools
    MCP -->|Future: Direct Access| GitHub
    MCP -->|Future: Direct Access| Jira
    MCP -->|Future: Direct Access| Slack
    MCP -->|Future: Direct Access| Sentry

    APIEndpoint -->|Registers| ServiceRegistry

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class AgentContainer,AgentEngine,Worker,ExternalServices,GitHub,Jira,Slack,Sentry,ServicesContainer,ServicesAPI,APIEndpoint,ServiceRegistry,MCPServer,MCP,MCPTools,ServiceManagement,APIKeyManager,ServiceProxy,WebhookAPI,WebhookReceiver,KnowledgeGraph,KGAPI,KGEngine defaultNode
```

### Service Access Methods:

1. **MCP (Model Context Protocol)**
   - Direct integration with external services
   - Tool discovery and execution
   - No API key management needed in agent
   - Supports GitHub, Jira, Slack operations

2. **External Service with API Keys**
   - Centralized API key management
   - Service proxy for unified access
   - Secure credential storage
   - Supports all external services

---

## 9. Agent Capabilities & Resources

```mermaid
graph TB
    subgraph AgentContainer["Agent Container"]

        subgraph Skills["Available Skills"]
            direction LR
            GitHubSkill["github-operations<br/>PRs, Issues, Actions"]
            JiraSkill["jira-operations<br/>Issues, Sprints, Boards"]
            SlackSkill["slack-operations<br/>Messages, Channels"]
            WebhookSkill["webhook-management<br/>Create, Edit, Test"]
            TestingSkill["testing<br/>Test Creation, Validation"]
            VerificationSkill["verification<br/>Script-based Verification"]
            OtherSkills["... More Skills"]
        end

        subgraph Agents["Available Agents"]
            direction LR
            PlanningAgent["planning<br/>Task Planning"]
            ExecutorAgent["executor<br/>Task Execution"]
            VerifierAgent["verifier<br/>Verification"]
            GitHubIssueAgent["github-issue-handler<br/>Issue Management"]
            GitHubPRAgent["github-pr-review<br/>PR Review"]
            JiraCodeAgent["jira-code-plan<br/>Code Planning"]
            OtherAgents["... More Agents"]
        end

        subgraph Repositories["Repository Access"]
            direction TB
            TmpFolder["tmp/<br/>Temporary Storage"]
            Repo1["Repository 1<br/>Cloned for Task"]
            Repo2["Repository 2<br/>Cloned for Task"]
            RepoN["Repository N<br/>..."]
        end

        subgraph AgentEngine["Agent Engine"]
            Engine["Engine<br/>Orchestrates Skills & Agents"]
        end
    end

    subgraph WebhookAPI["Webhook API"]
        WebhookReceiver["Webhook Receiver<br/>/webhooks/*"]
    end

    subgraph KnowledgeGraph["Knowledge Graph API (External)"]
        direction TB
        KGAPI["Knowledge Graph API<br/>External Service"]
        KGEngine["Knowledge Graph Engine<br/>Entity Relationships<br/>Context Storage"]
        Entities["Entities<br/>People, Projects, Issues"]
        Relationships["Relationships<br/>Connections, Dependencies"]
        Context["Context<br/>Historical Information"]
    end

    subgraph ExternalServices["External Services"]
        GitHub["GitHub"]
        Jira["Jira"]
        Slack["Slack"]
    end

    GitHub -->|Webhooks| WebhookReceiver
    Jira -->|Webhooks| WebhookReceiver
    Slack -->|Webhooks| WebhookReceiver

    WebhookReceiver -->|Webhook Events| KGAPI
    KGAPI -->|Processes| KGEngine
    KGEngine -->|Manages| Entities
    KGEngine -->|Manages| Relationships
    KGEngine -->|Stores| Context

    AgentEngine -->|Loads| Skills
    AgentEngine -->|Loads| Agents
    AgentEngine -->|Manages| Repositories
    AgentEngine -->|Queries| KGAPI
    Engine -->|Queries| KGAPI
    Engine -->|Updates| KGAPI

    Skills -->|Can Use| GitHubSkill
    Skills -->|Can Use| JiraSkill
    Skills -->|Can Use| SlackSkill
    Skills -->|Can Use| WebhookSkill
    Skills -->|Can Use| TestingSkill
    Skills -->|Can Use| VerificationSkill

    Agents -->|Can Use| PlanningAgent
    Agents -->|Can Use| ExecutorAgent
    Agents -->|Can Use| VerifierAgent
    Agents -->|Can Use| GitHubIssueAgent
    Agents -->|Can Use| GitHubPRAgent
    Agents -->|Can Use| JiraCodeAgent

    TmpFolder -->|Contains| Repo1
    TmpFolder -->|Contains| Repo2
    TmpFolder -->|Contains| RepoN

    KGEngine -->|Manages| Entities
    KGEngine -->|Manages| Relationships
    KGEngine -->|Stores| Context

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class AgentContainer,Skills,GitHubSkill,JiraSkill,SlackSkill,WebhookSkill,TestingSkill,VerificationSkill,OtherSkills,Agents,PlanningAgent,ExecutorAgent,VerifierAgent,GitHubIssueAgent,GitHubPRAgent,JiraCodeAgent,OtherAgents,Repositories,TmpFolder,Repo1,Repo2,RepoN,WebhookAPI,WebhookReceiver,KnowledgeGraph,KGAPI,KGEngine,Entities,Relationships,Context,AgentEngine,Engine,ExternalServices,GitHub,Jira,Slack defaultNode
```

### Agent Capabilities:

1. **Skills Library**
   - Pre-built skills for common operations
   - GitHub, Jira, Slack integrations
   - Webhook management
   - Testing and verification capabilities
   - Extensible through `.claude/skills/`

2. **Agent Library**
   - Specialized agents for different tasks
   - Planning, execution, verification agents
   - Domain-specific agents (GitHub, Jira)
   - Extensible through `.claude/agents/`

3. **Repository Access**
   - Can clone relevant repositories to `tmp/` folder
   - Isolated workspace per task
   - Automatic cleanup after task completion

4. **Knowledge Graph API (External)**
   - External API service separate from agent container
   - Receives data through webhooks from GitHub, Jira, and Slack
   - Webhook API forwards events to Knowledge Graph API
   - Entity relationship tracking
   - Context preservation across tasks
   - Historical information storage
   - Agent queries and updates knowledge graph through API

---

## 10. Configuration Management

```mermaid
graph TB
    subgraph RootConfig["Root Directory"]
        RootClaude["claude.md<br/>Global Configuration"]

        subgraph RootSections["Global Configuration Sections"]
            direction LR
            GlobalRules["Global Rules"]
            GlobalSkills["Global Skills"]
            GlobalAgents["Global Agents"]
            GlobalCommands["Global Commands"]
            GlobalHooks["Global Hooks"]
            GlobalWebhooks["Global Webhooks"]
        end
    end

    subgraph AgentConfig["Agent Container"]
        AgentClaude["claude.md<br/>Agent-specific Configuration"]

        subgraph AgentSections["Agent Configuration Sections"]
            direction LR
            AgentRules["Agent Rules"]
            AgentSkills["Agent Skills"]
            AgentCommands["Agent Commands"]
            AgentHooks["Agent Hooks"]
        end
    end

    subgraph ExternalConfig["External Container"]
        ExternalClaude["claude.md<br/>External Configuration"]

        subgraph ExternalSections["External Configuration Sections"]
            direction LR
            ExternalRules["External Rules"]
            ExternalConfigSect["External Config"]
        end
    end

    RootClaude -->|Inherits/Defines| AgentClaude
    RootClaude -->|Inherits/Defines| ExternalClaude

    RootClaude -->|Defines| GlobalRules
    RootClaude -->|Defines| GlobalSkills
    RootClaude -->|Defines| GlobalAgents
    RootClaude -->|Defines| GlobalCommands
    RootClaude -->|Defines| GlobalHooks
    RootClaude -->|Defines| GlobalWebhooks

    AgentClaude -->|Extends| AgentRules
    AgentClaude -->|Extends| AgentSkills
    AgentClaude -->|Extends| AgentCommands
    AgentClaude -->|Extends| AgentHooks

    ExternalClaude -->|Extends| ExternalRules
    ExternalClaude -->|Extends| ExternalConfigSect

    GlobalRules -.->|Base| AgentRules
    GlobalSkills -.->|Base| AgentSkills
    GlobalCommands -.->|Base| AgentCommands
    GlobalHooks -.->|Base| AgentHooks

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class RootConfig,RootClaude,GlobalRules,GlobalSkills,GlobalAgents,GlobalCommands,GlobalHooks,GlobalWebhooks,AgentConfig,AgentClaude,AgentRules,AgentSkills,AgentCommands,AgentHooks,ExternalConfig,ExternalClaude,ExternalRules,ExternalConfigSect defaultNode
```

---

## 11. Summary

### Main Components:

1. **Agent Container**
   - Internal dashboard for managing agents, skills, rules
   - Direct chat interface with the agent
   - Real-time task logs
   - Task execution engine
   - Independent configuration (claude.md)
   - **Skills**: github-operations, jira-operations, slack-operations, webhook-management, testing, verification, and more
   - **Agents**: planning, executor, verifier, github-issue-handler, github-pr-review, jira-code-plan, and more
   - **Repository Access**: Can clone and work with relevant repositories in `tmp/` folder
   - **External Service Access**:
     - Through Services Container (External) - API or MCP
     - Accesses GitHub, Jira, Slack, Sentry services

2. **Task Queue**
   - Redis-based queue connecting webhooks to agents
   - Decouples webhook reception from agent processing
   - Enables load balancing and task distribution

3. **External Container**
   - Dashboard for statistics and costs
   - Historical logs viewing
   - Webhook, command, and trigger management
   - API for application data

4. **API Gateway**
   - Webhook API - event reception and routing to queue
   - Routes API calls to Services Container

5. **Services Container (External)**
   - External container separate from API Gateway
   - Services API endpoint `/api/services/*` - REST API
   - MCP Server for service integration (future support)
   - API Keys Manager for GitHub/Jira/Slack/Sentry
   - Service Proxy for unified API access
   - Provides access to external services (GitHub, Jira, Slack, Sentry)
   - Can work as API or MCP (Model Context Protocol)

6. **Knowledge Graph API (External Service)**
   - External API service separate from agent container
   - Receives data through webhooks from GitHub, Jira, and Slack
   - Webhook API forwards events to Knowledge Graph API
   - Entity relationship tracking
   - Context preservation across tasks
   - Historical information storage
   - Agent queries and updates knowledge graph through API

7. **Hierarchical Configuration**
   - Root claude.md - global settings
   - Agent claude.md - agent-specific settings
   - External claude.md - external settings

### Architecture Benefits:

- **Scaling**: Ability to run multiple agent instances
- **Separation**: Clear separation between execution (agent), monitoring (external), and service access (services container)
- **Flexibility**: Easy replacement of agent container, services container, and knowledge graph
- **Centralized Management**: Webhook and trigger management from one place
- **Modular Configuration**: Each container with its own claude.md
- **Queue-Based Architecture**: Decoupled webhook processing through task queue
- **Extensibility**: Skills and agents can be added dynamically
- **Repository Access**: Agents can work with cloned repositories in isolated tmp folders
- **Knowledge Management**: External Knowledge Graph API that receives data through webhooks from GitHub/Jira/Slack
- **Service Integration**: External Services Container provides unified access to GitHub/Jira/Slack/Sentry via API or MCP
- **Webhook-Based Knowledge Graph**: Knowledge Graph API receives events through webhooks, not direct API calls
- **External Services Container**: Separate container for service access, can work as REST API or MCP (future)
- **API Gateway Separation**: Webhook API in gateway, Services API in external container
