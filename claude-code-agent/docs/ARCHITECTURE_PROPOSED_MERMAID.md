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
    end

    subgraph Gateway["API Gateway"]
        WebhookAPI["Webhook API<br/>/webhooks/*"]
        ServicesAPI["Services API<br/>/api/services/*"]
    end

    subgraph Agent["Agent Container"]
        AgentDesc["Task Execution<br/>Internal Management<br/>Internal Dashboard"]
    end

    subgraph External["External Container"]
        ExternalDesc["Statistics<br/>Logs<br/>Webhook Management"]
    end

    subgraph Root["Root Directory"]
        RootDesc["claude.md<br/>docker-compose.yml<br/>Central Configuration"]
    end

    Services -->|Webhooks| WebhookAPI
    Services -->|API Calls| ServicesAPI

    WebhookAPI -->|Route| Agent
    WebhookAPI -->|Store| External
    ServicesAPI -->|Call| Agent
    ServicesAPI -->|Data| External

    Agent -->|Logs/Metrics| External

    Root -.->|Configures| Gateway
    Root -.->|Configures| Agent
    Root -.->|Configures| External

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Services,GitHub,Jira,Slack,Gateway,WebhookAPI,ServicesAPI,Agent,AgentDesc,External,ExternalDesc,Root,RootDesc defaultNode
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
            Skills["Skills<br/>.claude/skills/"]
            Agents["Agents<br/>.claude/agents/"]
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

    ClaudeMD -.->|Configures| Engine
    Dockerfile -.->|Builds| AgentContainer
    MainPy -.->|Implements| Engine

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class AgentContainer,AgentDashboard,AgentMgmt,SkillsMgmt,RulesMgmt,ChatUI,TaskLogsUI,AgentCore,Engine,Queue,Worker,CLIExec,AgentConfig,Rules,Skills,Agents,Commands,Hooks,AgentFiles,Dockerfile,ClaudeMD,MainPy,Requirements,AgentStorage,LocalDB,LocalLogs defaultNode
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
            Router["Webhook Router<br/>Route to Agents<br/>Load Balancing"]
        end

        subgraph ServicesAPI["Services API"]
            direction TB
            Endpoint["Services Endpoint<br/>/api/services/*<br/>Service Calls"]
            Registry["Service Registry<br/>Service Registration<br/>Discovery, Health Checks"]
        end
    end

    subgraph Agent["Agent Container"]
        AgentContainer["Agent Container"]
    end

    subgraph External["External Container"]
        ExternalContainer["External Container"]
    end

    Services -->|Webhook Events| Receiver
    Services -->|API Calls| Endpoint

    Receiver -->|Validates| Validator
    Validator -->|Routes| Router
    Router -->|Routes Tasks| AgentContainer
    Router -->|Stores Events| ExternalContainer

    Endpoint -->|Service Calls| AgentContainer
    Endpoint -->|Service Data| ExternalContainer
    Endpoint -->|Registers| Registry

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Services,GitHub,Jira,Slack,Sentry,APIGateway,WebhookAPI,Receiver,Validator,Router,ServicesAPI,Endpoint,Registry,Agent,AgentContainer,External,ExternalContainer defaultNode
```

---

## 5. Data Flow

### 5.1 Webhook Event Flow

```mermaid
sequenceDiagram
    autonumber
    participant ExtService as External Service
    participant WebhookAPI as Webhook API
    participant Agent as Agent Container
    participant External as External Container
    participant User as User

    Note over ExtService,User: Webhook Event Flow
    ExtService->>WebhookAPI: 1. Webhook Event
    WebhookAPI->>WebhookAPI: 2. Validate Signature
    WebhookAPI->>Agent: 3. Route to Agent
    Agent->>Agent: 4. Process Task
    Agent->>External: 5. Send Logs
    Agent->>External: 6. Send Metrics
    Agent->>External: 7. Send Costs
    External->>External: 8. Store in Database
    External->>User: 9. Display in Dashboard
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
    participant External as External Container

    Note over User,External: Chat with Agent Flow
    User->>AgentDashboard: 1. Send Chat Message
    AgentDashboard->>AgentEngine: 2. Process Chat
    AgentEngine->>CLI: 3. Execute Claude CLI
    CLI->>AgentEngine: 4. Return Response
    AgentEngine->>AgentDashboard: 5. Stream Response
    AgentDashboard->>User: 6. Display Response
    AgentEngine->>External: 7. Log Chat Interaction
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

    ExternalDir --> ExternalDockerfile
    ExternalDir --> ExternalClaude
    ExternalDir --> ExternalMain
    ExternalDir --> ExternalDashboard
    ExternalDir --> ExternalAPI

    RootClaude -.->|Defines| AgentClaude
    RootClaude -.->|Defines| ExternalClaude

    classDef defaultNode fill:#000000,stroke:#ffffff,stroke-width:2px,color:#ffffff

    class Root,RootClaude,RootDocker,RootEnv,RootMakefile,AgentDir,AgentDockerfile,AgentClaude,AgentMain,AgentRequirements,AgentConfig,AgentClaudeDir,AgentRules,AgentSkills,AgentAgents,ExternalDir,ExternalDockerfile,ExternalClaude,ExternalMain,ExternalDashboard,ExternalAPI defaultNode
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
        SharedQueue["Shared Queue<br/>Redis<br/>Task Distribution"]
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

## 8. Configuration Management

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

## 9. Summary

### Main Components:

1. **Agent Container**
   - Internal dashboard for managing agents, skills, rules
   - Direct chat interface with the agent
   - Real-time task logs
   - Task execution engine
   - Independent configuration (claude.md)

2. **External Container**
   - Dashboard for statistics and costs
   - Historical logs viewing
   - Webhook, command, and trigger management
   - API for application data

3. **API Gateway**
   - Webhook API - event reception and routing
   - Services API - service calls

4. **Hierarchical Configuration**
   - Root claude.md - global settings
   - Agent claude.md - agent-specific settings
   - External claude.md - external settings

### Architecture Benefits:

- **Scaling**: Ability to run multiple agent instances
- **Separation**: Clear separation between execution (agent) and monitoring (external)
- **Flexibility**: Easy replacement of agent container
- **Centralized Management**: Webhook and trigger management from one place
- **Modular Configuration**: Each container with its own claude.md
