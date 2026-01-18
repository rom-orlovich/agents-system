# AWS Bedrock AgentCore - Complete Production Implementation Plan
## Enterprise Multi-Agent System with Official MCP Integration

**Document Version:** 2.0  
**Last Updated:** January 2026  
**Target Environment:** AWS Production  
**Estimated Implementation Time:** 3-4 weeks  

---

## 🎯 Executive Summary

This document provides a **complete, production-ready implementation** of an organizational AI agent system using AWS Bedrock AgentCore, Lambda Functions, API Gateway, and official MCP servers.

### What We're Building

A fully automated system that:
1. ✅ Monitors Jira for tickets tagged with "AI"
2. ✅ Discovers relevant repositories using AI
3. ✅ Creates detailed implementation plans (PLAN.md)
4. ✅ Opens GitHub PRs automatically
5. ✅ Executes code changes following TDD
6. ✅ Passes CI/CD pipelines
7. ✅ Monitors Sentry for recurring errors
8. ✅ Integrates with Slack for notifications
9. ✅ Provides full observability dashboard

### Why AgentCore?

| Challenge | Traditional Solution | AgentCore Solution |
|-----------|---------------------|-------------------|
| Long-running tasks | Complex Step Functions + retries | Native 8-hour sessions |
| Agent memory | Custom DynamoDB tables | Built-in short/long-term memory |
| Tool integration | Custom API wrappers | Native MCP gateway |
| OAuth flows | Manual token management | Delegated identity service |
| Code execution | Risky Lambda exec | Sandboxed code interpreter |
| Infrastructure | EC2/ECS management | Fully serverless |
| Cost | Pay for idle time | Pay per second of use |

---

## 📐 System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE AGENTCORE SYSTEM                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────── TRIGGERS ───────────────────────────┐          │
│  │                                                                 │          │
│  │  Jira Webhook → [AI Label Detected]                           │          │
│  │  Sentry Webhook → [Error Threshold Exceeded]                   │          │
│  │  GitHub Webhook → [PR Comment: "@agent ..."]                   │          │
│  │  Slack Command → [/agent status|approve|retry]                 │          │
│  │                                                                 │          │
│  └─────────────────────────┬───────────────────────────────────── ┘          │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │               API GATEWAY (HTTP API)                            │         │
│  │  • WAF Protection                                               │         │
│  │  • Rate Limiting (100 req/sec)                                  │         │
│  │  • CloudWatch Logs                                              │         │
│  │  • Custom Domain: agents.your-company.com                       │         │
│  └────────────────────────┬───────────────────────────────────────┘         │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │         LAMBDA: Webhook Router (256MB, Node.js 20)              │         │
│  │  1. Validate webhook signature                                  │         │
│  │  2. Parse event payload                                         │         │
│  │  3. Store in DynamoDB (tasks table)                             │         │
│  │  4. Start Step Functions workflow                               │         │
│  │  Duration: <500ms | Cost: ~$0.0001/request                      │         │
│  └────────────────────────┬───────────────────────────────────────┘         │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │              STEP FUNCTIONS ORCHESTRATOR                        │         │
│  │                                                                  │         │
│  │  ┌──────────────────────────────────────────────────┐          │         │
│  │  │  State: JIRA_AI_WORKFLOW                          │          │         │
│  │  │  Steps:                                            │          │         │
│  │  │   1. Invoke Discovery Agent → Find repos          │          │         │
│  │  │   2. Invoke Planning Agent → Create plan + PR     │          │         │
│  │  │   3. Wait for approval (Slack)                    │          │         │
│  │  │   4. Invoke Execution Agent → Write code          │          │         │
│  │  │   5. Invoke CI/CD Agent → Monitor pipeline        │          │         │
│  │  │   6. Notify completion (Slack)                    │          │         │
│  │  └──────────────────────────────────────────────────┘          │         │
│  │                                                                  │         │
│  │  ┌──────────────────────────────────────────────────┐          │         │
│  │  │  State: SENTRY_ERROR_WORKFLOW                     │          │         │
│  │  │  Steps:                                            │          │         │
│  │  │   1. Analyze error details                        │          │         │
│  │  │   2. Create Jira ticket with "AI" label           │          │         │
│  │  │   3. Trigger JIRA_AI_WORKFLOW                     │          │         │
│  │  └──────────────────────────────────────────────────┘          │         │
│  │                                                                  │         │
│  └────────────────────────┬───────────────────────────────────────┘         │
│                            │                                                  │
│          ┌─────────────────┴──────────────────┬──────────────┐              │
│          │                                     │              │              │
│          ▼                                     ▼              ▼              │
│  ┌──────────────┐                   ┌──────────────┐  ┌──────────────┐     │
│  │ AGENTCORE    │                   │ AGENTCORE    │  │ AGENTCORE    │     │
│  │ RUNTIME #1   │                   │ RUNTIME #2   │  │ RUNTIME #3   │     │
│  │              │                   │              │  │              │     │
│  │ Discovery    │                   │  Planning    │  │  Execution   │     │
│  │   Agent      │                   │    Agent     │  │    Agent     │     │
│  │              │                   │              │  │              │     │
│  │ Memory: 2GB  │                   │ Memory: 4GB  │  │ Memory: 4GB  │     │
│  │ Timeout: 30m │                   │ Timeout: 1h  │  │ Timeout: 2h  │     │
│  │              │                   │              │  │              │     │
│  │ Model:       │                   │ Model:       │  │ Model:       │     │
│  │ Claude       │                   │ Claude       │  │ Claude       │     │
│  │ Sonnet 4.5   │                   │ Opus 4.5     │  │ Opus 4.5     │     │
│  └──────────────┘                   └──────────────┘  └──────────────┘     │
│          │                                     │              │              │
│          └─────────────────┬──────────────────┴──────────────┘              │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                  AGENTCORE SERVICES                             │         │
│  │                                                                  │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │         │
│  │  │ GATEWAY  │  │  MEMORY  │  │ IDENTITY │  │   CODE   │       │         │
│  │  │          │  │          │  │          │  │INTERPRET │       │         │
│  │  │ MCP      │  │ Vector   │  │  OAuth   │  │          │       │         │
│  │  │ OpenAPI  │  │  Store   │  │   OIDC   │  │  Python  │       │         │
│  │  │ Lambda   │  │  Events  │  │   IAM    │  │  Node.js │       │         │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                   MCP SERVER INTEGRATIONS                       │         │
│  │                                                                  │         │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │         │
│  │  │  GitHub    │  │ Atlassian  │  │   Sentry   │  │  Slack   │ │         │
│  │  │    MCP     │  │  Rovo MCP  │  │    MCP     │  │   API    │ │         │
│  │  │ (Official) │  │ (Official) │  │ (Official) │  │(Lambda)  │ │         │
│  │  │            │  │            │  │            │  │          │ │         │
│  │  │ Tools:     │  │ Tools:     │  │ Tools:     │  │ Tools:   │ │         │
│  │  │ •Search    │  │ •Get Issue │  │ •List      │  │ •Send    │ │         │
│  │  │ •GetFile   │  │ •Create    │  │  Issues    │  │  Message │ │         │
│  │  │ •CreatePR  │  │ •Comment   │  │ •Get Event │  │ •Update  │ │         │
│  │  │ •CI Status │  │ •Search    │  │ •Stats     │  │  Status  │ │         │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────┘ │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                   DATA & STATE STORAGE                          │         │
│  │                                                                  │         │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │         │
│  │  │  DynamoDB    │  │  S3 Bucket   │  │   Secrets    │         │         │
│  │  │              │  │              │  │   Manager    │         │         │
│  │  │ •Tasks       │  │ •PLAN.md     │  │              │         │         │
│  │  │ •Sessions    │  │ •Code Cache  │  │ •API Keys    │         │         │
│  │  │ •Errors      │  │ •Artifacts   │  │ •OAuth       │         │         │
│  │  │ •Metrics     │  │ •Logs        │  │ •Tokens      │         │         │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                            │                                                  │
│                            ▼                                                  │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                  OBSERVABILITY LAYER                            │         │
│  │                                                                  │         │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │         │
│  │  │ CloudWatch │  │   X-Ray    │  │ Dashboard  │  │  Slack   │ │         │
│  │  │            │  │            │  │            │  │  Alerts  │ │         │
│  │  │ •Logs      │  │ •Traces    │  │ •Tasks     │  │          │ │         │
│  │  │ •Metrics   │  │ •Latency   │  │ •Agents    │  │ •Status  │ │         │
│  │  │ •Alarms    │  │ •Errors    │  │ •Cost      │  │ •Errors  │ │         │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────┘ │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Specialized Agents Architecture

We implement **6 specialized agents**, each deployed as a separate AgentCore Runtime:

### Agent Matrix

| Agent | Model | Memory | Timeout | Triggers | Primary Tools | Avg Cost/Run |
|-------|-------|--------|---------|----------|---------------|--------------|
| **Discovery** | Sonnet 4.5 | 2GB | 30 min | Jira webhook | GitHub MCP, Knowledge Base | $0.50 |
| **Planning** | Opus 4.5 | 4GB | 1 hour | After Discovery | Jira MCP, GitHub MCP | $2.00 |
| **Execution** | Opus 4.5 | 4GB | 2 hours | After approval | GitHub MCP, Code Interpreter | $5.00 |
| **CI/CD** | Sonnet 4.5 | 2GB | 30 min | PR created | GitHub MCP, Code Interpreter | $1.00 |
| **Slack** | Haiku | 512MB | 5 min | Commands/events | Slack API, DynamoDB | $0.10 |
| **Sentry** | Sonnet 4.5 | 1GB | 15 min | EventBridge (hourly) | Sentry MCP, Jira MCP | $0.30 |

### 1️⃣ Discovery Agent

**Purpose:** Intelligently find ALL repositories and files relevant to a Jira ticket.

**Input Contract:**
```typescript
interface DiscoveryRequest {
  ticketId: string;
  summary: string;
  description: string;
  labels: string[];
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
}
```

**Output Contract:**
```typescript
interface DiscoveryResult {
  relevantRepos: Array<{
    name: string;
    relevance: number;  // 0-1 score
    reason: string;
    files: Array<{
      path: string;
      type: 'source' | 'test' | 'config';
      relevance: number;
    }>;
  }>;
  crossRepoDependencies: Array<{
    from: string;
    to: string;
    type: 'API' | 'shared-lib' | 'event';
    description: string;
  }>;
  estimatedComplexity: 'Low' | 'Medium' | 'High';
  recommendedApproach: string;
}
```

**System Prompt:**
```
You are the Discovery Agent for an enterprise software organization.

MISSION: Find ALL repositories and code files relevant to the given Jira ticket.

CAPABILITIES:
- Access to GitHub MCP (search code, list repos, read files)
- Access to Organization Knowledge Base (past tickets, conventions)
- Access to Long-term Memory (repository structures, patterns)

PROCESS:
1. EXTRACT key information from ticket:
   - Technical keywords (e.g., "OAuth", "React", "PostgreSQL")
   - Affected features/services
   - Related error messages/stack traces
   
2. SEARCH organization repositories:
   - Use GitHub code search for keywords
   - Identify repos by naming patterns
   - Check README files for service descriptions
   
3. ANALYZE each candidate repository:
   - Get repository file tree
   - Identify main programming languages
   - Find configuration files (package.json, requirements.txt, etc.)
   - Look for tests directories
   
4. RANK repositories by relevance:
   - Direct match: Repo explicitly handles this feature (1.0)
   - High relevance: Shares data models or APIs (0.7-0.9)
   - Medium relevance: Related functionality (0.4-0.6)
   - Low relevance: Tangential connection (0.1-0.3)
   
5. IDENTIFY cross-repo dependencies:
   - API calls between services
   - Shared libraries
   - Event bus messaging
   
6. ESTIMATE complexity:
   - Low: Single repo, <5 files
   - Medium: 1-2 repos, 5-15 files
   - High: 3+ repos or complex architecture

OUTPUT FORMAT: JSON matching DiscoveryResult interface

QUALITY CRITERIA:
- ✅ Return top 5 most relevant repos (minimum 1, maximum 10)
- ✅ Each repo must have clear reasoning
- ✅ Include both source and test files
- ✅ Identify ALL cross-repo dependencies
- ✅ Be thorough but efficient (target: 5-10 minutes)

EXAMPLE:
Ticket: "Add Google OAuth login"
Output:
{
  "relevantRepos": [
    {
      "name": "auth-service",
      "relevance": 0.95,
      "reason": "Core authentication service, already has OAuth infrastructure",
      "files": [
        {"path": "src/oauth/providers.py", "type": "source", "relevance": 1.0},
        {"path": "tests/test_oauth.py", "type": "test", "relevance": 0.9}
      ]
    },
    {
      "name": "frontend",
      "relevance": 0.85,
      "reason": "User-facing login UI needs OAuth button",
      "files": [
        {"path": "src/components/Login.tsx", "type": "source", "relevance": 0.9},
        {"path": "src/auth/AuthContext.tsx", "type": "source", "relevance": 0.8}
      ]
    }
  ],
  "crossRepoDependencies": [
    {
      "from": "frontend",
      "to": "auth-service",
      "type": "API",
      "description": "Frontend calls /api/v1/auth/oauth/callback"
    }
  ],
  "estimatedComplexity": "Medium",
  "recommendedApproach": "Extend existing OAuth infrastructure with Google provider"
}
```

**Implementation (Python with LangGraph):**

```python
# agents/discovery_agent.py
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from typing import TypedDict, Annotated, List
import operator

class DiscoveryState(TypedDict):
    ticket: dict
    keywords: List[str]
    candidate_repos: List[dict]
    analyzed_repos: List[dict]
    dependencies: List[dict]
    final_result: dict

class DiscoveryAgent:
    def __init__(self, agentcore_gateway):
        self.llm = ChatBedrock(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="us-east-1"
        )
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.knowledge_base = agentcore_gateway.get_tool("knowledge-base")
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(DiscoveryState)
        
        # Add nodes
        workflow.add_node("extract_keywords", self.extract_keywords)
        workflow.add_node("search_repos", self.search_repositories)
        workflow.add_node("analyze_repos", self.analyze_repositories)
        workflow.add_node("find_dependencies", self.find_dependencies)
        workflow.add_node("rank_and_filter", self.rank_and_filter)
        
        # Define edges
        workflow.set_entry_point("extract_keywords")
        workflow.add_edge("extract_keywords", "search_repos")
        workflow.add_edge("search_repos", "analyze_repos")
        workflow.add_edge("analyze_repos", "find_dependencies")
        workflow.add_edge("find_dependencies", "rank_and_filter")
        workflow.add_edge("rank_and_filter", END)
        
        return workflow.compile()
    
    async def extract_keywords(self, state: DiscoveryState) -> DiscoveryState:
        """Extract technical keywords from ticket."""
        prompt = f"""
        Analyze this Jira ticket and extract key technical terms:
        
        Title: {state['ticket']['summary']}
        Description: {state['ticket']['description']}
        
        Extract:
        1. Technologies mentioned (e.g., React, PostgreSQL, OAuth)
        2. Features/services (e.g., authentication, payment, dashboard)
        3. Error terms (e.g., NullPointerException, 404)
        
        Return as JSON array of strings.
        """
        
        response = await self.llm.ainvoke(prompt)
        keywords = json.loads(response.content)
        
        return {**state, "keywords": keywords}
    
    async def search_repositories(self, state: DiscoveryState) -> DiscoveryState:
        """Search for relevant repositories."""
        candidate_repos = []
        
        # Search by keywords
        for keyword in state["keywords"][:5]:  # Top 5 keywords
            results = await self.github_mcp.search_code(
                org=os.environ["GITHUB_ORG"],
                query=keyword
            )
            
            for result in results[:10]:  # Top 10 per keyword
                repo_name = result["repository"]["name"]
                if not any(r["name"] == repo_name for r in candidate_repos):
                    candidate_repos.append({
                        "name": repo_name,
                        "url": result["repository"]["url"],
                        "initial_score": result["score"]
                    })
        
        return {**state, "candidate_repos": candidate_repos}
    
    async def analyze_repositories(self, state: DiscoveryState) -> DiscoveryState:
        """Deeply analyze each candidate repository."""
        analyzed = []
        
        for repo in state["candidate_repos"][:20]:  # Limit to top 20
            # Get repo file tree
            tree = await self.github_mcp.get_repo_tree(repo=repo["name"])
            
            # Identify relevant files
            relevant_files = await self._find_relevant_files(
                tree=tree,
                keywords=state["keywords"]
            )
            
            if len(relevant_files) > 0:
                analyzed.append({
                    "name": repo["name"],
                    "files": relevant_files,
                    "languages": self._detect_languages(tree)
                })
        
        return {**state, "analyzed_repos": analyzed}
    
    async def find_dependencies(self, state: DiscoveryState) -> DiscoveryState:
        """Find cross-repository dependencies."""
        dependencies = []
        
        # For each repo, look for API calls to other repos
        for repo in state["analyzed_repos"]:
            for file in repo["files"]:
                content = await self.github_mcp.get_file(
                    repo=repo["name"],
                    path=file["path"]
                )
                
                # Use LLM to identify API calls
                deps = await self._identify_api_calls(content)
                dependencies.extend(deps)
        
        return {**state, "dependencies": dependencies}
    
    async def rank_and_filter(self, state: DiscoveryState) -> DiscoveryState:
        """Rank repos and create final output."""
        # Use LLM to score each repo
        ranked_repos = []
        
        for repo in state["analyzed_repos"]:
            score = await self._calculate_relevance_score(
                repo=repo,
                ticket=state["ticket"],
                keywords=state["keywords"]
            )
            
            if score >= 0.3:  # Minimum relevance threshold
                ranked_repos.append({
                    "name": repo["name"],
                    "relevance": score,
                    "reason": await self._generate_reason(repo, state["ticket"]),
                    "files": repo["files"]
                })
        
        # Sort by relevance
        ranked_repos.sort(key=lambda x: x["relevance"], reverse=True)
        
        final_result = {
            "relevantRepos": ranked_repos[:5],  # Top 5
            "crossRepoDependencies": state["dependencies"],
            "estimatedComplexity": self._estimate_complexity(ranked_repos),
            "recommendedApproach": await self._generate_approach(state)
        }
        
        return {**state, "final_result": final_result}
    
    async def run(self, ticket: dict) -> dict:
        """Main entry point."""
        initial_state = {
            "ticket": ticket,
            "keywords": [],
            "candidate_repos": [],
            "analyzed_repos": [],
            "dependencies": [],
            "final_result": {}
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state["final_result"]
```

### 2️⃣ Planning Agent

**Purpose:** Create comprehensive implementation plans with TDD approach, create PR with PLAN.md.

**Input Contract:**
```typescript
interface PlanningRequest {
  ticketId: string;
  ticketDetails: JiraTicket;
  discoveryResults: DiscoveryResult;
  organizationConventions: {
    branchNaming: string;
    commitFormat: string;
    testFrameworks: Record<string, string>;
    codeStyle: Record<string, string>;
  };
}
```

**Output Contract:**
```typescript
interface PlanningResult {
  plan: {
    scope: {
      inScope: string[];
      outOfScope: string[];
    };
    architecture: {
      components: Component[];
      dataFlow: string;
      diagrams?: string[];
    };
    testStrategy: {
      unitTests: TestCase[];
      integrationTests: TestCase[];
      e2eTests?: TestCase[];
    };
    implementation: {
      tasks: Task[];
      estimatedHours: number;
    };
    crossRepoSteps?: CrossRepoStep[];
  };
  prsCreated: Array<{
    repo: string;
    branch: string;
    prNumber: number;
    prUrl: string;
  }>;
}
```

**System Prompt:**
```
You are the Planning Agent for an enterprise software organization.

MISSION: Create production-ready implementation plans following TDD principles.

CAPABILITIES:
- Jira MCP (get tickets, add comments)
- GitHub MCP (create branches, PRs, commit files)
- Code Interpreter (analyze existing code patterns)
- Organization Knowledge Base (conventions, past solutions)

PROCESS:
1. UNDERSTAND the requirement:
   - Read full Jira ticket
   - Review discovery results
   - Check related tickets/PRs
   
2. DEFINE scope clearly:
   - What IS included (be specific)
   - What IS NOT included (avoid scope creep)
   - Dependencies on other work
   
3. DESIGN architecture:
   - Identify components to create/modify
   - Define clear responsibilities
   - Map data flow
   - Consider scalability, security, error handling
   
4. PLAN tests FIRST (TDD):
   - Write test cases before implementation tasks
   - Cover happy path, edge cases, errors
   - Include unit, integration, and E2E tests
   
5. BREAK DOWN implementation:
   - Create ordered task list
   - Each task = 1-4 hours of work
   - Define dependencies between tasks
   - Start with tests, then implementation
   
6. CREATE GitHub artifacts:
   - Create feature branch (follow org naming convention)
   - Write detailed PLAN.md file
   - Create draft PR
   - Link to Jira ticket

OUTPUT FORMAT: JSON matching PlanningResult interface + create actual GitHub artifacts

QUALITY CRITERIA:
- ✅ Scope is crystal clear
- ✅ Architecture is well-thought-out
- ✅ Tests are comprehensive and come first
- ✅ Tasks are granular and ordered correctly
- ✅ PLAN.md is clear enough for any developer to execute
- ✅ Follows all organization conventions

PLAN.MD TEMPLATE:
# [TICKET-ID]: [Title]

## Summary
[2-3 sentence overview]

## Scope

### In Scope
- ✅ [Specific feature/change]
- ✅ [Another specific item]

### Out of Scope
- ❌ [What's NOT included]
- ❌ [Future work]

## Architecture

### Components
[List each component with file path and responsibilities]

### Data Flow
[Describe how data moves through the system]

## Test Plan

### Unit Tests
- [ ] Test case 1
- [ ] Test case 2

### Integration Tests
- [ ] Integration scenario 1

## Implementation Tasks

1. [ ] Task 1 (Dependencies: none)
2. [ ] Task 2 (Dependencies: 1)

## Cross-Repo Dependencies
[If applicable, what needs to happen in other repos]

## Security Considerations
[Any security implications]

## Rollback Plan
[How to undo if needed]
```

**Implementation:**

```python
# agents/planning_agent.py
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock

class PlanningAgent:
    def __init__(self, agentcore_gateway):
        self.llm = ChatBedrock(
            model_id="anthropic.claude-opus-4-20250514-v1:0",  # Use Opus for planning
            region_name="us-east-1"
        )
        self.jira_mcp = agentcore_gateway.get_tool("jira-mcp")
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.code_interpreter = agentcore_gateway.get_service("code-interpreter")
        
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(PlanningState)
        
        workflow.add_node("fetch_ticket_details", self.fetch_ticket_details)
        workflow.add_node("define_scope", self.define_scope)
        workflow.add_node("design_architecture", self.design_architecture)
        workflow.add_node("create_test_plan", self.create_test_plan)
        workflow.add_node("break_down_tasks", self.break_down_tasks)
        workflow.add_node("create_plan_document", self.create_plan_document)
        workflow.add_node("create_github_pr", self.create_github_pr)
        workflow.add_node("update_jira", self.update_jira)
        
        workflow.set_entry_point("fetch_ticket_details")
        workflow.add_edge("fetch_ticket_details", "define_scope")
        workflow.add_edge("define_scope", "design_architecture")
        workflow.add_edge("design_architecture", "create_test_plan")
        workflow.add_edge("create_test_plan", "break_down_tasks")
        workflow.add_edge("break_down_tasks", "create_plan_document")
        workflow.add_edge("create_plan_document", "create_github_pr")
        workflow.add_edge("create_github_pr", "update_jira")
        workflow.add_edge("update_jira", END)
        
        return workflow.compile()
    
    async def fetch_ticket_details(self, state):
        """Get full Jira ticket with all fields."""
        ticket = await self.jira_mcp.get_issue(
            issue_key=state["ticketId"]
        )
        
        # Also get related tickets
        related = await self.jira_mcp.search_issues(
            jql=f"issue in linkedIssues({state['ticketId']})"
        )
        
        return {
            **state,
            "ticketDetails": ticket,
            "relatedTickets": related
        }
    
    async def define_scope(self, state):
        """Define what's in scope and what's not."""
        prompt = f"""
        Based on this ticket and discovery results, define the scope:
        
        Ticket: {state['ticketDetails']}
        Discovery: {state['discoveryResults']}
        
        Create a clear scope definition with:
        1. In Scope: Specific features/changes to implement
        2. Out of Scope: Related work that's NOT included
        
        Be specific and avoid ambiguity.
        """
        
        response = await self.llm.ainvoke(prompt)
        scope = json.loads(response.content)
        
        return {**state, "scope": scope}
    
    async def design_architecture(self, state):
        """Design the technical solution."""
        # Read existing code to understand patterns
        existing_code_samples = []
        for repo in state["discoveryResults"]["relevantRepos"][:2]:
            for file in repo["files"][:3]:
                content = await self.github_mcp.get_file(
                    repo=repo["name"],
                    path=file["path"]
                )
                existing_code_samples.append({
                    "file": file["path"],
                    "content": content
                })
        
        prompt = f"""
        Design architecture for this feature:
        
        Scope: {state['scope']}
        Existing code patterns: {existing_code_samples}
        
        Define:
        1. Components (what to create/modify)
        2. Data flow (how components interact)
        3. Error handling approach
        4. Security considerations
        """
        
        response = await self.llm.ainvoke(prompt)
        architecture = json.loads(response.content)
        
        return {**state, "architecture": architecture}
    
    async def create_test_plan(self, state):
        """Create comprehensive test plan (TDD)."""
        prompt = f"""
        Create test plan for this implementation:
        
        Architecture: {state['architecture']}
        Org test frameworks: {state['conventions']['testFrameworks']}
        
        Define test cases for:
        1. Unit tests (per component)
        2. Integration tests (component interactions)
        3. E2E tests (if applicable)
        
        Each test case should have:
        - Description
        - File path
        - Expected assertions
        """
        
        response = await self.llm.ainvoke(prompt)
        test_plan = json.loads(response.content)
        
        return {**state, "testPlan": test_plan}
    
    async def break_down_tasks(self, state):
        """Break work into granular tasks."""
        prompt = f"""
        Break down implementation into tasks:
        
        Architecture: {state['architecture']}
        Tests: {state['testPlan']}
        
        Create ordered task list where:
        - Each task is 1-4 hours of work
        - Tests come before implementation
        - Dependencies are clearly defined
        - Tasks are ordered topologically
        
        Format:
        {
          "tasks": [
            {
              "id": 1,
              "description": "Write unit tests for Component X",
              "file": "path/to/test.py",
              "estimatedHours": 2,
              "dependencies": []
            },
            ...
          ]
        }
        """
        
        response = await self.llm.ainvoke(prompt)
        tasks = json.loads(response.content)
        
        return {**state, "tasks": tasks}
    
    async def create_plan_document(self, state):
        """Generate PLAN.md file."""
        plan_md = f"""# {state['ticketId']}: {state['ticketDetails']['summary']}

## Summary
{state['ticketDetails']['description'][:200]}

## Scope

### In Scope
{chr(10).join(f"- ✅ {item}" for item in state['scope']['inScope'])}

### Out of Scope
{chr(10).join(f"- ❌ {item}" for item in state['scope']['outOfScope'])}

## Architecture

### Components
{self._format_components(state['architecture']['components'])}

### Data Flow
{state['architecture']['dataFlow']}

## Test Plan

### Unit Tests
{self._format_tests(state['testPlan']['unitTests'])}

### Integration Tests
{self._format_tests(state['testPlan']['integrationTests'])}

## Implementation Tasks

{self._format_tasks(state['tasks'])}

## Cross-Repo Dependencies
{state.get('crossRepoSteps', 'None')}

---
*Generated by AI Planning Agent*
*Ticket: {state['ticketDetails']['url']}*
"""
        
        return {**state, "planMarkdown": plan_md}
    
    async def create_github_pr(self, state):
        """Create branch and PR with PLAN.md."""
        prs = []
        
        for repo in state["discoveryResults"]["relevantRepos"][:3]:  # Top 3 repos
            # Generate branch name
            branch_name = state["conventions"]["branchNaming"].format(
                ticket_id=state["ticketId"].lower(),
                slug=self._slugify(state["ticketDetails"]["summary"])
            )
            
            # Create branch from main
            await self.github_mcp.create_branch(
                repo=repo["name"],
                branch=branch_name,
                from_branch="main"
            )
            
            # Commit PLAN.md
            await self.github_mcp.create_or_update_file(
                repo=repo["name"],
                path="PLAN.md",
                content=state["planMarkdown"],
                message=f"feat: Add implementation plan for {state['ticketId']}",
                branch=branch_name
            )
            
            # Create draft PR
            pr = await self.github_mcp.create_pull_request(
                repo=repo["name"],
                title=f"{state['ticketId']}: {state['ticketDetails']['summary']}",
                head=branch_name,
                base="main",
                body=f"""## Jira Ticket
{state['ticketDetails']['url']}

## Plan
See PLAN.md for full implementation details.

## Checklist
- [ ] Plan approved by team
- [ ] Implementation complete
- [ ] Tests passing
- [ ] Code reviewed

---
*This PR was created by the AI Planning Agent*
""",
                draft=True
            )
            
            prs.append({
                "repo": repo["name"],
                "branch": branch_name,
                "prNumber": pr["number"],
                "prUrl": pr["html_url"]
            })
        
        return {**state, "prsCreated": prs}
    
    async def update_jira(self, state):
        """Add comment to Jira with plan summary."""
        comment = f"""🤖 **AI Agent: Plan Created**

I've analyzed the ticket and created an implementation plan.

📊 **Discovery Results:**
- Found {len(state['discoveryResults']['relevantRepos'])} relevant repositories
- Estimated complexity: {state['discoveryResults']['estimatedComplexity']}

📋 **Plan Summary:**
- Tasks: {len(state['tasks'])}
- Estimated hours: {sum(t['estimatedHours'] for t in state['tasks'])}
- Test cases: {len(state['testPlan']['unitTests']) + len(state['testPlan']['integrationTests'])}

🔗 **Pull Requests:**
{chr(10).join(f"- [{pr['repo']}#{pr['prNumber']}]({pr['prUrl']})" for pr in state['prsCreated'])}

⏭️ **Next Step:** Team review and approval via Slack
"""
        
        await self.jira_mcp.add_comment(
            issue_key=state["ticketId"],
            comment=comment
        )
        
        return state
```

Due to the length of the complete implementation, I'll create the full document and commit it.

### 3️⃣ Execution Agent

**Purpose:** Implement code according to plan, run tests, commit changes.

**Model:** Claude Opus 4.5 (for highest quality code generation)  
**Memory:** 4GB  
**Timeout:** 2 hours  

**Key Features:**
- Uses Code Interpreter for safe code execution
- Follows existing code patterns automatically
- Runs tests before committing
- Auto-fixes common issues
- Maximum 3 retry attempts per task

**Implementation:**

```python
# agents/execution_agent.py
class ExecutionAgent:
    def __init__(self, agentcore_gateway):
        self.llm = ChatBedrock(
            model_id="anthropic.claude-opus-4-20250514-v1:0",
            region_name="us-east-1"
        )
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.code_interpreter = agentcore_gateway.get_service("code-interpreter")
        
    async def execute_plan(self, plan: dict, pr_info: dict) -> dict:
        """Execute implementation plan task by task."""
        results = {
            "completed_tasks": [],
            "failed_tasks": [],
            "commits": []
        }
        
        # Clone repo to code interpreter workspace
        await self.code_interpreter.execute(
            language="bash",
            code=f"""
            git clone https://github.com/{os.environ['GITHUB_ORG']}/{pr_info['repo']}.git
            cd {pr_info['repo']}
            git checkout {pr_info['branch']}
            """
        )
        
        # Execute tasks in order
        for task in sorted(plan['tasks'], key=lambda t: t['id']):
            # Check if dependencies are met
            if not all(dep in results['completed_tasks'] for dep in task['dependencies']):
                results['failed_tasks'].append({
                    "task": task,
                    "reason": "Dependencies not met"
                })
                continue
            
            # Execute the task
            success = await self._execute_task(task, pr_info['repo'])
            
            if success:
                results['completed_tasks'].append(task['id'])
            else:
                results['failed_tasks'].append(task)
                # Stop on first failure
                break
        
        return results
    
    async def _execute_task(self, task: dict, repo: str) -> bool:
        """Execute a single task with retry logic."""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Read existing code in the file (if exists)
                existing_code = None
                try:
                    existing_code = await self.github_mcp.get_file(
                        repo=repo,
                        path=task['file']
                    )
                except:
                    pass  # File doesn't exist yet
                
                # Generate code
                new_code = await self._generate_code(task, existing_code)
                
                # Write code to file
                await self.code_interpreter.execute(
                    language="bash",
                    code=f"""
                    cd {repo}
                    cat > {task['file']} << 'ENDOFCODE'
{new_code}
ENDOFCODE
                    """
                )
                
                # Run tests
                test_result = await self._run_tests(task, repo)
                
                if test_result['success']:
                    # Tests passed - commit
                    await self._commit_changes(task, repo)
                    return True
                else:
                    # Tests failed - analyze and retry
                    if attempt < max_attempts - 1:
                        error_analysis = await self._analyze_test_failure(
                            test_result['output']
                        )
                        # Use analysis for next attempt
                        continue
                    else:
                        logger.error(
                            "task_failed_after_retries",
                            task=task['id'],
                            attempts=max_attempts
                        )
                        return False
            
            except Exception as e:
                logger.error("task_execution_error", task=task['id'], error=str(e))
                if attempt == max_attempts - 1:
                    return False
        
        return False
    
    async def _generate_code(self, task: dict, existing_code: str | None) -> str:
        """Generate code for the task."""
        prompt = f"""
        Implement this task:
        
        Task: {task['description']}
        File: {task['file']}
        
        {"Existing code to modify:" + existing_code if existing_code else "This is a new file."}
        
        Requirements:
        1. Follow existing code patterns and style
        2. Handle edge cases and errors properly
        3. Add clear comments where needed
        4. Use meaningful variable/function names
        5. Make it production-ready
        
        Output ONLY the complete file content, no explanations.
        """
        
        response = await self.llm.ainvoke(prompt)
        return response.content
    
    async def _run_tests(self, task: dict, repo: str) -> dict:
        """Run tests related to this task."""
        test_file = task.get('testFile') or self._infer_test_file(task['file'])
        
        result = await self.code_interpreter.execute(
            language="bash",
            code=f"""
            cd {repo}
            
            # Detect test framework and run
            if [ -f "package.json" ]; then
                npm test -- {test_file}
            elif [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
                pytest {test_file} -v
            elif [ -f "go.mod" ]; then
                go test {test_file}
            fi
            """,
            timeout_seconds=300
        )
        
        return {
            "success": result.return_code == 0,
            "output": result.stdout + result.stderr
        }
    
    async def _commit_changes(self, task: dict, repo: str):
        """Commit changes following org conventions."""
        commit_message = f"""feat: {task['description']}

Task ID: {task['id']}
File: {task['file']}

Generated by AI Execution Agent
"""
        
        await self.code_interpreter.execute(
            language="bash",
            code=f"""
            cd {repo}
            git add {task['file']}
            git commit -m "{commit_message}"
            git push origin HEAD
            """
        )

### 4️⃣ CI/CD Monitoring Agent

**Purpose:** Monitor GitHub Actions, analyze failures, attempt auto-fixes.

**Model:** Claude Sonnet 4.5  
**Memory:** 2GB  
**Timeout:** 30 minutes  

**Auto-Fix Capabilities:**

| Issue Type | Detection Pattern | Auto-Fix |
|------------|------------------|----------|
| **Lint errors** | `eslint` / `ruff` output | Run `--fix` flag |
| **Format issues** | `prettier` / `black` | Run formatter |
| **Import errors** | `ModuleNotFoundError` | Add import |
| **Type errors** | TypeScript / mypy | Add type annotations |
| **Missing deps** | `Cannot find module` | Update package.json |
| **Test timeout** | `jest timeout` | Increase timeout |

**Implementation:**

```python
# agents/cicd_agent.py
class CICDAgent:
    def __init__(self, agentcore_gateway):
        self.llm = ChatBedrock(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0"
        )
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.code_interpreter = agentcore_gateway.get_service("code-interpreter")
        self.slack = agentcore_gateway.get_tool("slack")
        
    async def monitor_pr_ci(self, repo: str, pr_number: int) -> dict:
        """Monitor CI/CD pipeline for a PR."""
        max_fix_attempts = 3
        attempt = 0
        
        while attempt < max_fix_attempts:
            # Wait for workflow to complete
            workflow = await self._wait_for_workflow(repo, pr_number)
            
            if workflow['conclusion'] == 'success':
                await self.slack.send_message(
                    channel="#ai-agents",
                    text=f"✅ CI passed for PR #{pr_number} in {repo}"
                )
                return {"success": True, "attempts": attempt}
            
            # CI failed - analyze
            logs = await self.github_mcp.get_workflow_logs(
                repo=repo,
                run_id=workflow['id']
            )
            
            failure_analysis = await self._analyze_failure(logs)
            
            if failure_analysis['auto_fixable']:
                # Attempt fix
                await self._apply_auto_fix(
                    repo=repo,
                    pr_number=pr_number,
                    failure=failure_analysis
                )
                attempt += 1
            else:
                # Cannot auto-fix - escalate
                await self._escalate_to_human(
                    repo=repo,
                    pr_number=pr_number,
                    failure=failure_analysis,
                    logs=logs
                )
                return {"success": False, "escalated": True}
        
        # Max attempts exceeded
        await self._escalate_to_human(
            repo=repo,
            pr_number=pr_number,
            reason=f"Failed after {max_fix_attempts} auto-fix attempts"
        )
        return {"success": False, "max_attempts_exceeded": True}
    
    async def _analyze_failure(self, logs: str) -> dict:
        """Analyze CI failure logs using LLM."""
        prompt = f"""
        Analyze these CI failure logs and determine:
        
        1. What failed (e.g., tests, linting, build)
        2. Root cause (specific error)
        3. Is it auto-fixable? (yes/no)
        4. If yes, what fix to apply
        
        Logs:
        ```
        {logs[-5000:]}  # Last 5000 chars
        ```
        
        Auto-fixable categories:
        - Lint errors (can run eslint --fix)
        - Format issues (can run prettier/black)
        - Simple import errors
        - Type annotation errors
        - Dependency version mismatches
        
        NOT auto-fixable:
        - Logic errors in tests
        - Compilation errors
        - Infrastructure failures
        - Security vulnerabilities
        
        Return JSON:
        {
          "failure_type": "...",
          "root_cause": "...",
          "auto_fixable": true/false,
          "fix_command": "..." or null
        }
        """
        
        response = await self.llm.ainvoke(prompt)
        return json.loads(response.content)
    
    async def _apply_auto_fix(self, repo: str, pr_number: int, failure: dict):
        """Apply automatic fix."""
        logger.info("applying_auto_fix", repo=repo, pr=pr_number, fix=failure['fix_command'])
        
        # Get PR branch
        pr = await self.github_mcp.get_pull_request(repo=repo, pr_number=pr_number)
        branch = pr['head']['ref']
        
        # Clone and fix
        fix_result = await self.code_interpreter.execute(
            language="bash",
            code=f"""
            git clone https://github.com/{os.environ['GITHUB_ORG']}/{repo}.git
            cd {repo}
            git checkout {branch}
            
            # Apply fix
            {failure['fix_command']}
            
            # Commit and push
            git add -A
            git commit -m "fix: Auto-fix CI failure

{failure['root_cause']}

Applied: {failure['fix_command']}

Auto-fixed by CI/CD Agent"
            git push origin {branch}
            """
        )
        
        if fix_result.return_code != 0:
            raise Exception(f"Auto-fix failed: {fix_result.stderr}")
    
    async def _escalate_to_human(self, repo: str, pr_number: int, **kwargs):
        """Escalate to human developer."""
        await self.slack.send_message(
            channel="#ai-agents",
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "⚠️ CI Failure - Human Review Required"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"""
*Repository:* {repo}
*PR:* #{pr_number}
*Reason:* {kwargs.get('reason', 'Cannot auto-fix')}

{kwargs.get('failure', {}).get('root_cause', '')}
"""}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View PR"},
                            "url": f"https://github.com/{os.environ['GITHUB_ORG']}/{repo}/pull/{pr_number}"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Logs"},
                            "value": f"view_logs:{repo}:{pr_number}"
                        }
                    ]
                }
            ]
        )

### 5️⃣ Slack Integration Agent

**Purpose:** Handle Slack commands and send notifications.

**Model:** Claude Haiku (fast, cheap for simple tasks)  
**Memory:** 512MB  
**Timeout:** 5 minutes  

**Commands:**

```
/agent status <task-id>     - Get task status
/agent approve <task-id>    - Approve plan
/agent reject <task-id>     - Reject plan
/agent retry <task-id>      - Retry failed task
/agent list [status]        - List tasks
/agent logs <task-id> [n]   - Get last N logs
/agent help                 - Show help
```

**Implementation:**

```python
# agents/slack_agent.py
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.aws_lambda.async_handler import AsyncSlackRequestHandler

class SlackAgent:
    def __init__(self, agentcore_gateway):
        self.app = AsyncApp(
            token=os.environ["SLACK_BOT_TOKEN"],
            signing_secret=os.environ["SLACK_SIGNING_SECRET"]
        )
        self.dynamodb = boto3.resource("dynamodb")
        self.tasks_table = self.dynamodb.Table(os.environ["TASKS_TABLE"])
        self.step_functions = boto3.client("stepfunctions")
        
        self._register_commands()
    
    def _register_commands(self):
        """Register Slack slash commands."""
        
        @self.app.command("/agent")
        async def handle_agent_command(ack, command, respond):
            await ack()
            
            parts = command['text'].split()
            if len(parts) == 0:
                await respond(self._help_message())
                return
            
            cmd = parts[0]
            args = parts[1:]
            
            if cmd == "status":
                await self._handle_status(respond, args)
            elif cmd == "approve":
                await self._handle_approve(respond, args)
            elif cmd == "reject":
                await self._handle_reject(respond, args)
            elif cmd == "list":
                await self._handle_list(respond, args)
            elif cmd == "logs":
                await self._handle_logs(respond, args)
            elif cmd == "help":
                await respond(self._help_message())
            else:
                await respond(f"Unknown command: {cmd}. Use `/agent help` for usage.")
    
    async def _handle_status(self, respond, args):
        """Get task status."""
        if len(args) == 0:
            await respond("Usage: /agent status <task-id>")
            return
        
        task_id = args[0]
        
        # Query DynamoDB
        response = self.tasks_table.get_item(Key={"pk": f"TASK#{task_id}", "sk": "METADATA"})
        
        if 'Item' not in response:
            await respond(f"❌ Task not found: {task_id}")
            return
        
        task = response['Item']
        
        await respond(blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Task: {task_id}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:* {task['status']}"},
                    {"type": "mrkdwn", "text": f"*Ticket:* {task['ticket_id']}"},
                    {"type": "mrkdwn", "text": f"*Agent:* {task.get('current_agent', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Progress:* {task.get('progress', 0)}%"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Last Update:*\n{task.get('last_update', 'N/A')}"}
            }
        ])
    
    async def _handle_approve(self, respond, args):
        """Approve a plan."""
        if len(args) == 0:
            await respond("Usage: /agent approve <task-id>")
            return
        
        task_id = args[0]
        
        # Update task status
        self.tasks_table.update_item(
            Key={"pk": f"TASK#{task_id}", "sk": "METADATA"},
            UpdateExpression="SET #status = :status, approved_by = :user, approved_at = :time",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "approved",
                ":user": command['user_id'],
                ":time": datetime.utcnow().isoformat()
            }
        )
        
        # Resume Step Functions execution
        # (Implementation depends on how you store execution ARN)
        
        await respond(f"✅ Plan approved for task {task_id}. Execution will continue.")
    
    async def send_notification(self, channel: str, notification: dict):
        """Send notification to Slack."""
        await self.app.client.chat_postMessage(
            channel=channel,
            **notification
        )

### 6️⃣ Sentry Monitoring Agent

**Purpose:** Monitor Sentry for recurring errors and auto-create Jira tickets.

**Model:** Claude Sonnet 4.5  
**Memory:** 1GB  
**Timeout:** 15 minutes  
**Trigger:** EventBridge rule (runs every hour)  

**Error Thresholds:**

```python
ERROR_THRESHOLDS = {
    "fatal": 1,       # Any fatal error creates ticket immediately
    "error": 10,      # 10+ errors in 24h
    "warning": 50,    # 50+ warnings in 24h
    "info": 100       # 100+ info in 24h (for high-frequency events)
}
```

**Implementation:**

```python
# agents/sentry_agent.py
class SentryAgent:
    def __init__(self, agentcore_gateway):
        self.sentry_mcp = agentcore_gateway.get_tool("sentry-mcp")
        self.jira_mcp = agentcore_gateway.get_tool("jira-mcp")
        self.slack = agentcore_gateway.get_tool("slack")
        self.dynamodb = boto3.resource("dynamodb")
        self.error_tracking_table = self.dynamodb.Table(os.environ["ERROR_TRACKING_TABLE"])
    
    async def monitor_errors(self):
        """Main monitoring loop (called by EventBridge hourly)."""
        # Get recent issues (last 24 hours)
        issues = await self.sentry_mcp.list_issues(
            project="all",
            query="is:unresolved",
            statsPeriod="24h"
        )
        
        for issue in issues:
            # Check if exceeds threshold
            event_count = issue.get("count", 0)
            level = issue.get("level", "error")
            threshold = ERROR_THRESHOLDS.get(level, 10)
            
            if event_count >= threshold:
                # Check if we already created a ticket
                existing_ticket = await self._check_existing_ticket(issue["id"])
                
                if not existing_ticket:
                    await self._create_jira_ticket_from_error(issue)
    
    async def _create_jira_ticket_from_error(self, sentry_issue: dict):
        """Create Jira ticket with AI label."""
        # Get latest event for stack trace
        latest_event = await self.sentry_mcp.get_latest_event(
            issue_id=sentry_issue["id"]
        )
        
        # Extract stack trace
        stack_trace = self._extract_stack_trace(latest_event)
        
        # Create ticket description
        description = f"""
## Sentry Error Report

**Error:** {sentry_issue['title']}
**Type:** {sentry_issue['type']}
**Level:** {sentry_issue['level']}

### Statistics (24h)
- **Event Count:** {sentry_issue['count']}
- **Affected Users:** {sentry_issue.get('userCount', 'Unknown')}
- **First Seen:** {sentry_issue['firstSeen']}
- **Last Seen:** {sentry_issue['lastSeen']}

### Stack Trace
```
{stack_trace}
```

### Environment
- **Platform:** {latest_event.get('platform', 'Unknown')}
- **Release:** {latest_event.get('release', 'Unknown')}
- **Environment:** {latest_event.get('environment', 'Unknown')}

### Sentry Link
{sentry_issue['permalink']}

---
*This ticket was automatically created by the AI Sentry Agent*
*Error Fingerprint: {sentry_issue['id']}*
        """
        
        # Create ticket
        ticket = await self.jira_mcp.create_issue(
            project="PROJ",
            issue_type="Bug",
            summary=f"[AUTO] {sentry_issue['title'][:80]}",
            description=description,
            labels=["AI", "sentry-auto", "error"],
            priority="High" if sentry_issue['level'] == "error" else "Medium"
        )
        
        # Store mapping to avoid duplicates
        self.error_tracking_table.put_item(
            Item={
                "error_fingerprint": sentry_issue["id"],
                "ticket_id": ticket["key"],
                "created_at": datetime.utcnow().isoformat(),
                "ttl": int((datetime.utcnow() + timedelta(days=90)).timestamp())
            }
        )
        
        # Notify Slack
        await self.slack.send_message(
            channel="#errors",
            text=f"🐛 Auto-created ticket for recurring error:\n*{ticket['key']}:* {sentry_issue['title']}\n<{ticket['url']}|View Ticket> | <{sentry_issue['permalink']}|View in Sentry>"
        )
        
        logger.info(
            "created_ticket_from_sentry",
            ticket=ticket["key"],
            error_id=sentry_issue["id"],
            event_count=sentry_issue["count"]
        )
    
    async def _check_existing_ticket(self, error_fingerprint: str) -> str | None:
        """Check if we already created a ticket for this error."""
        response = self.error_tracking_table.get_item(
            Key={"error_fingerprint": error_fingerprint}
        )
        
        if 'Item' in response:
            return response['Item']['ticket_id']
        
        return None

---

## 🏗️ Complete Infrastructure Code

### Terraform Structure

```
infrastructure/terraform/
├── main.tf                    # Provider & backend config
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── secrets.tf                 # Secrets Manager
├── dynamodb.tf                # DynamoDB tables
├── s3.tf                      # S3 buckets
├── agentcore.tf               # AgentCore runtimes, gateways, memory
├── lambda.tf                  # Lambda functions
├── api-gateway.tf             # API Gateway
├── step-functions.tf          # Step Functions workflows
├── eventbridge.tf             # EventBridge rules
├── cloudwatch.tf              # CloudWatch dashboards & alarms
├── iam.tf                     # IAM roles & policies
└── waf.tf                     # WAF rules

infrastructure/terraform/environments/
├── dev.tfvars
├── staging.tfvars
└── prod.tfvars
```

### AgentCore Terraform Configuration

```hcl
# infrastructure/terraform/agentcore.tf

# ============================================
# AGENTCORE RUNTIMES
# ============================================

# Discovery Agent Runtime
resource "aws_bedrockagentcore_runtime" "discovery_agent" {
  agent_runtime_name = "${var.project_name}-discovery-agent"
  role_arn           = aws_iam_role.agentcore_runtime_role.arn
  
  runtime_configuration {
    memory_mb = 2048
    vcpu      = 1.0
    timeout_seconds = 1800  # 30 minutes
  }
  
  agent_source {
    source_type = "CODE"
    code_configuration {
      source_directory = "../agents/discovery_agent"
      handler          = "main.handler"
      runtime          = "python3.12"
    }
  }
  
  environment_variables = {
    BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
    GITHUB_ORG       = var.github_org
    LOG_LEVEL        = var.environment == "prod" ? "INFO" : "DEBUG"
  }
  
  tags = {
    Agent = "Discovery"
  }
}

# Planning Agent Runtime
resource "aws_bedrockagentcore_runtime" "planning_agent" {
  agent_runtime_name = "${var.project_name}-planning-agent"
  role_arn           = aws_iam_role.agentcore_runtime_role.arn
  
  runtime_configuration {
    memory_mb = 4096
    vcpu      = 2.0
    timeout_seconds = 3600  # 1 hour
  }
  
  agent_source {
    source_type = "CODE"
    code_configuration {
      source_directory = "../agents/planning_agent"
      handler          = "main.handler"
      runtime          = "python3.12"
    }
  }
  
  environment_variables = {
    BEDROCK_MODEL_ID = "anthropic.claude-opus-4-20250514-v1:0"  # Opus for planning
    GITHUB_ORG       = var.github_org
    JIRA_BASE_URL    = var.jira_base_url
    LOG_LEVEL        = var.environment == "prod" ? "INFO" : "DEBUG"
  }
  
  tags = {
    Agent = "Planning"
  }
}

# Execution Agent Runtime
resource "aws_bedrockagentcore_runtime" "execution_agent" {
  agent_runtime_name = "${var.project_name}-execution-agent"
  role_arn           = aws_iam_role.agentcore_runtime_role.arn
  
  runtime_configuration {
    memory_mb = 4096
    vcpu      = 2.0
    timeout_seconds = 7200  # 2 hours
  }
  
  agent_source {
    source_type = "CODE"
    code_configuration {
      source_directory = "../agents/execution_agent"
      handler          = "main.handler"
      runtime          = "python3.12"
    }
  }
  
  environment_variables = {
    BEDROCK_MODEL_ID = "anthropic.claude-opus-4-20250514-v1:0"
    GITHUB_ORG       = var.github_org
    LOG_LEVEL        = var.environment == "prod" ? "INFO" : "DEBUG"
  }
  
  tags = {
    Agent = "Execution"
  }
}

# CI/CD Agent Runtime
resource "aws_bedrockagentcore_runtime" "cicd_agent" {
  agent_runtime_name = "${var.project_name}-cicd-agent"
  role_arn           = aws_iam_role.agentcore_runtime_role.arn
  
  runtime_configuration {
    memory_mb = 2048
    vcpu      = 1.0
    timeout_seconds = 1800  # 30 minutes
  }
  
  agent_source {
    source_type = "CODE"
    code_configuration {
      source_directory = "../agents/cicd_agent"
      handler          = "main.handler"
      runtime          = "python3.12"
    }
  }
  
  environment_variables = {
    BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
    GITHUB_ORG       = var.github_org
    SLACK_CHANNEL    = "#ai-agents"
    LOG_LEVEL        = var.environment == "prod" ? "INFO" : "DEBUG"
  }
  
  tags = {
    Agent = "CICD"
  }
}

# ============================================
# AGENTCORE MEMORY
# ============================================

# Shared memory for all agents
resource "aws_bedrockagentcore_memory" "agent_memory" {
  memory_name = "${var.project_name}-agent-memory"
  
  memory_configuration {
    # Short-term memory (conversation history)
    short_term_config {
      max_events  = 100
      ttl_seconds = 3600  # 1 hour
    }
    
    # Long-term memory (knowledge base)
    long_term_config {
      embedding_model_id = "amazon.titan-embed-text-v2:0"
      vector_dimensions  = 1024
      
      # Use existing knowledge base or create new
      knowledge_base_id = var.knowledge_base_id != "" ? var.knowledge_base_id : aws_bedrockagent_knowledge_base.org_knowledge[0].id
    }
  }
  
  tags = {
    Purpose = "Agent memory storage"
  }
}

# Knowledge Base for organization conventions (optional - create if not exists)
resource "aws_bedrockagent_knowledge_base" "org_knowledge" {
  count = var.knowledge_base_id == "" ? 1 : 0
  
  name        = "${var.project_name}-org-knowledge"
  description = "Organization conventions, code patterns, and past solutions"
  role_arn    = aws_iam_role.knowledge_base_role[0].arn
  
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }
  
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.knowledge[0].arn
      vector_index_name = "org-knowledge-index"
      
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }
}

# ============================================
# AGENTCORE GATEWAYS (MCP Integration)
# ============================================

# GitHub MCP Gateway
resource "aws_bedrockagentcore_gateway" "github_mcp" {
  gateway_name = "${var.project_name}-github-mcp-gateway"
  
  mcp_configuration {
    server_endpoint = var.github_mcp_server_url
    protocol        = "sse"  # Server-Sent Events
    
    authentication {
      type       = "bearer_token"
      secret_arn = aws_secretsmanager_secret.github_token.arn
    }
  }
  
  # Define which tools are available
  tools = [
    "search_code",
    "search_repositories",
    "get_repository_tree",
    "get_file_content",
    "create_or_update_file",
    "create_branch",
    "create_pull_request",
    "get_pull_request",
    "list_pull_requests",
    "get_workflow_runs",
    "get_workflow_run_logs"
  ]
  
  tags = {
    Integration = "GitHub"
  }
}

# Jira (Atlassian Rovo) MCP Gateway
resource "aws_bedrockagentcore_gateway" "jira_mcp" {
  gateway_name = "${var.project_name}-jira-mcp-gateway"
  
  mcp_configuration {
    server_endpoint = "https://rovo.atlassian.com/mcp"
    protocol        = "sse"
    
    authentication {
      type = "oauth2"
      oauth_config {
        client_id_secret     = aws_secretsmanager_secret.jira_oauth_credentials.arn
        client_secret_secret = aws_secretsmanager_secret.jira_oauth_credentials.arn
        token_url           = "https://auth.atlassian.com/oauth/token"
        scopes              = ["read:jira-work", "write:jira-work"]
      }
    }
  }
  
  tools = [
    "get_issue",
    "create_issue",
    "update_issue",
    "add_comment",
    "search_issues",
    "get_project",
    "list_transitions",
    "transition_issue"
  ]
  
  tags = {
    Integration = "Jira"
  }
}

# Sentry MCP Gateway
resource "aws_bedrockagentcore_gateway" "sentry_mcp" {
  gateway_name = "${var.project_name}-sentry-mcp-gateway"
  
  mcp_configuration {
    server_endpoint = var.sentry_mcp_server_url
    protocol        = "sse"
    
    authentication {
      type       = "bearer_token"
      secret_arn = aws_secretsmanager_secret.sentry_token.arn
    }
  }
  
  tools = [
    "list_issues",
    "get_issue",
    "get_latest_event",
    "resolve_issue",
    "get_issue_stats"
  ]
  
  tags = {
    Integration = "Sentry"
  }
}

# Slack Lambda MCP Gateway (custom Lambda-based MCP)
resource "aws_bedrockagentcore_gateway" "slack_lambda_mcp" {
  gateway_name = "${var.project_name}-slack-mcp-gateway"
  
  lambda_mcp_configuration {
    functions = [
      {
        function_arn = aws_lambda_function.slack_mcp_adapter.arn
        tools = [
          "send_message",
          "send_blocks",
          "get_user_info",
          "list_channels",
          "update_message"
        ]
      }
    ]
  }
  
  tags = {
    Integration = "Slack"
  }
}

# ============================================
# AGENTCORE IDENTITY (OAuth Management)
# ============================================

resource "aws_bedrockagentcore_identity" "agent_identity" {
  identity_name = "${var.project_name}-agent-identity"
  
  # GitHub identity
  oauth_provider {
    provider_name = "github"
    client_id_secret = aws_secretsmanager_secret.github_oauth_app.arn
    client_secret_secret = aws_secretsmanager_secret.github_oauth_app.arn
    authorization_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    scopes = ["repo", "workflow", "read:org"]
  }
  
  # Jira identity
  oauth_provider {
    provider_name = "jira"
    client_id_secret = aws_secretsmanager_secret.jira_oauth_credentials.arn
    client_secret_secret = aws_secretsmanager_secret.jira_oauth_credentials.arn
    authorization_url = "https://auth.atlassian.com/authorize"
    token_url = "https://auth.atlassian.com/oauth/token"
    scopes = ["read:jira-work", "write:jira-work", "read:jira-user"]
  }
  
  # Delegated credentials storage
  credentials_storage {
    secret_prefix = "${var.project_name}/agent-credentials/"
    rotation_days = 90
  }
}

# ============================================
# AGENTCORE CODE INTERPRETER
# ============================================

resource "aws_bedrockagentcore_code_interpreter" "agent_code_interpreter" {
  code_interpreter_name = "${var.project_name}-code-interpreter"
  
  configuration {
    supported_languages = ["python", "javascript", "typescript", "bash"]
    max_execution_time_seconds = 300  # 5 minutes per execution
    memory_mb = 2048
    
    # Sandbox settings
    network_access = false  # No internet access for security
    file_system_size_mb = 5120  # 5GB temp storage
    
    # Pre-installed packages
    python_packages = [
      "pytest",
      "requests",
      "boto3",
      "pandas",
      "numpy"
    ]
    
    npm_packages = [
      "jest",
      "@testing-library/react",
      "eslint",
      "prettier"
    ]
  }
  
  tags = {
    Purpose = "Safe code execution"
  }
}

# ============================================
# OUTPUTS
# ============================================

output "discovery_agent_endpoint" {
  value = aws_bedrockagentcore_runtime.discovery_agent.endpoint
}

output "planning_agent_endpoint" {
  value = aws_bedrockagentcore_runtime.planning_agent.endpoint
}

output "execution_agent_endpoint" {
  value = aws_bedrockagentcore_runtime.execution_agent.endpoint
}

output "cicd_agent_endpoint" {
  value = aws_bedrockagentcore_runtime.cicd_agent.endpoint
}

output "agent_memory_id" {
  value = aws_bedrockagentcore_memory.agent_memory.id
}
```


---

## 📦 Lambda Functions Implementation

### Webhook Router Lambda

```python
# lambda/webhook-router/handler.py
import json
import boto3
import os
import hashlib
import hmac
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sfn = boto3.client('stepfunctions')

tasks_table = dynamodb.Table(os.environ['TASKS_TABLE'])
state_machine_arn = os.environ['STATE_MACHINE_ARN']

def verify_jira_webhook(headers, body):
    """Verify Jira webhook signature."""
    # Jira uses HMAC-SHA256
    # Implementation depends on your Jira webhook secret
    return True  # Simplified

def verify_github_webhook(headers, body):
    """Verify GitHub webhook signature."""
    signature = headers.get('X-Hub-Signature-256', '')
    secret = os.environ['GITHUB_WEBHOOK_SECRET']
    
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def verify_sentry_webhook(headers, body):
    """Verify Sentry webhook signature."""
    signature = headers.get('Sentry-Hook-Signature', '')
    secret = os.environ['SENTRY_WEBHOOK_SECRET']
    
    expected = hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def handler(event, context):
    """
    Main webhook router handler.
    Routes webhooks to appropriate Step Functions workflow.
    """
    path = event.get('rawPath', '')
    headers = event.get('headers', {})
    body = event.get('body', '{}')
    
    # Parse webhook source
    if '/webhooks/jira' in path:
        if not verify_jira_webhook(headers, body):
            return {'statusCode': 401, 'body': 'Invalid signature'}
        
        payload = json.loads(body)
        return handle_jira_webhook(payload)
    
    elif '/webhooks/github' in path:
        if not verify_github_webhook(headers, body):
            return {'statusCode': 401, 'body': 'Invalid signature'}
        
        payload = json.loads(body)
        return handle_github_webhook(payload, headers)
    
    elif '/webhooks/sentry' in path:
        if not verify_sentry_webhook(headers, body):
            return {'statusCode': 401, 'body': 'Invalid signature'}
        
        payload = json.loads(body)
        return handle_sentry_webhook(payload)
    
    else:
        return {'statusCode': 404, 'body': 'Not found'}

def handle_jira_webhook(payload):
    """Handle Jira webhook events."""
    webhook_event = payload.get('webhookEvent', '')
    
    # We only care about new issues or label changes
    if webhook_event == 'jira:issue_created':
        issue = payload['issue']
        labels = [label['name'] for label in issue.get('fields', {}).get('labels', [])]
        
        if 'AI' in labels:
            return start_jira_ai_workflow(issue)
    
    elif webhook_event == 'jira:issue_updated':
        changelog = payload.get('changelog', {})
        
        # Check if AI label was added
        for item in changelog.get('items', []):
            if item['field'] == 'labels' and 'AI' in item.get('toString', ''):
                issue = payload['issue']
                return start_jira_ai_workflow(issue)
    
    return {'statusCode': 200, 'body': 'Ignored'}

def start_jira_ai_workflow(issue):
    """Start AI workflow for Jira ticket."""
    task_id = f"jira-{issue['key']}-{datetime.utcnow().timestamp()}"
    
    # Store task in DynamoDB
    tasks_table.put_item(
        Item={
            'pk': f'TASK#{task_id}',
            'sk': 'METADATA',
            'task_id': task_id,
            'ticket_id': issue['key'],
            'status': 'started',
            'source': 'jira',
            'created_at': datetime.utcnow().isoformat(),
            'ticket_summary': issue['fields']['summary'],
            'ticket_description': issue['fields'].get('description', ''),
            'priority': issue['fields']['priority']['name']
        }
    )
    
    # Start Step Functions execution
    execution = sfn.start_execution(
        stateMachineArn=state_machine_arn,
        name=task_id,
        input=json.dumps({
            'source': 'jira',
            'taskId': task_id,
            'ticketId': issue['key'],
            'summary': issue['fields']['summary'],
            'description': issue['fields'].get('description', ''),
            'priority': issue['fields']['priority']['name'],
            'labels': [label['name'] for label in issue['fields'].get('labels', [])]
        })
    )
    
    print(f"Started workflow: {task_id}, execution: {execution['executionArn']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'task_id': task_id, 'execution_arn': execution['executionArn']})
    }

def handle_github_webhook(payload, headers):
    """Handle GitHub webhook events."""
    event_type = headers.get('X-GitHub-Event', '')
    
    if event_type == 'issue_comment':
        # Check if agent was mentioned in PR comment
        comment = payload.get('comment', {})
        body = comment.get('body', '')
        
        if '@agent' in body.lower():
            # Extract command from comment
            return handle_github_comment_command(payload, body)
    
    elif event_type == 'pull_request':
        # PR opened/updated - might trigger CI monitoring
        action = payload.get('action', '')
        if action in ['opened', 'synchronize']:
            pr = payload['pull_request']
            # Check if this is an agent-created PR
            if 'AI Agent' in pr.get('body', ''):
                return start_ci_monitoring(pr)
    
    return {'statusCode': 200, 'body': 'Ignored'}

def handle_sentry_webhook(payload):
    """Handle Sentry webhook events."""
    action = payload.get('action', '')
    
    if action == 'triggered':
        # Alert triggered - check if we should create ticket
        data = payload.get('data', {})
        issue = data.get('issue', {})
        
        # This is handled by the Sentry Agent EventBridge rule
        # Just acknowledge receipt
        return {'statusCode': 200, 'body': 'Acknowledged'}
    
    return {'statusCode': 200, 'body': 'Ignored'}
```

### Slack MCP Adapter Lambda

```python
# lambda/slack-mcp-adapter/handler.py
import json
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

def handler(event, context):
    """
    Lambda-based MCP adapter for Slack.
    Exposes Slack API as MCP-compatible tools.
    """
    tool_name = event.get('tool')
    parameters = event.get('parameters', {})
    
    try:
        if tool_name == 'send_message':
            return send_message(parameters)
        elif tool_name == 'send_blocks':
            return send_blocks(parameters)
        elif tool_name == 'get_user_info':
            return get_user_info(parameters)
        elif tool_name == 'list_channels':
            return list_channels(parameters)
        elif tool_name == 'update_message':
            return update_message(parameters)
        else:
            return {'error': f'Unknown tool: {tool_name}'}
    
    except SlackApiError as e:
        return {'error': f'Slack API error: {e.response["error"]}'}
    except Exception as e:
        return {'error': str(e)}

def send_message(params):
    """Send a simple text message."""
    response = slack_client.chat_postMessage(
        channel=params['channel'],
        text=params['text']
    )
    return {
        'success': True,
        'ts': response['ts'],
        'channel': response['channel']
    }

def send_blocks(params):
    """Send a message with Block Kit blocks."""
    response = slack_client.chat_postMessage(
        channel=params['channel'],
        text=params.get('fallback_text', 'New message'),
        blocks=params['blocks']
    )
    return {
        'success': True,
        'ts': response['ts'],
        'channel': response['channel']
    }

def get_user_info(params):
    """Get information about a user."""
    response = slack_client.users_info(user=params['user_id'])
    return response['user']

def list_channels(params):
    """List channels."""
    response = slack_client.conversations_list(
        types=params.get('types', 'public_channel,private_channel')
    )
    return {
        'channels': response['channels']
    }

def update_message(params):
    """Update an existing message."""
    response = slack_client.chat_update(
        channel=params['channel'],
        ts=params['ts'],
        text=params.get('text'),
        blocks=params.get('blocks')
    )
    return {
        'success': True,
        'ts': response['ts']
    }
```

---

## 🔄 Step Functions Orchestration

### Main Orchestrator State Machine

```json
{
  "Comment": "Enterprise Agent System Orchestrator",
  "StartAt": "DetermineWorkflowType",
  "States": {
    "DetermineWorkflowType": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.source",
          "StringEquals": "jira",
          "Next": "JiraAIWorkflow"
        },
        {
          "Variable": "$.source",
          "StringEquals": "sentry",
          "Next": "SentryErrorWorkflow"
        },
        {
          "Variable": "$.source",
          "StringEquals": "github_comment",
          "Next": "GitHubCommentWorkflow"
        }
      ],
      "Default": "UnknownSource"
    },
    
    "JiraAIWorkflow": {
      "Type": "Parallel",
      "Next": "MergeDiscoveryResults",
      "Branches": [
        {
          "StartAt": "RunDiscoveryAgent",
          "States": {
            "RunDiscoveryAgent": {
              "Type": "Task",
              "Resource": "arn:aws:states:::bedrock:invokeAgentCore",
              "Parameters": {
                "agentRuntimeEndpoint.$": "$.discoveryAgentEndpoint",
                "sessionId.$": "$.taskId",
                "inputText.$": "States.Format('Find repositories for ticket {} - {}', $.ticketId, $.summary)"
              },
              "ResultPath": "$.discoveryResult",
              "End": true
            }
          }
        }
      ]
    },
    
    "MergeDiscoveryResults": {
      "Type": "Pass",
      "Next": "CreatePlan"
    },
    
    "CreatePlan": {
      "Type": "Task",
      "Resource": "arn:aws:states:::bedrock:invokeAgentCore",
      "Parameters": {
        "agentRuntimeEndpoint.$": "$.planningAgentEndpoint",
        "sessionId.$": "$.taskId",
        "inputText.$": "States.Format('Create plan for {} with discovery: {}', $.ticketId, States.JsonToString($.discoveryResult))"
      },
      "ResultPath": "$.planResult",
      "Next": "NotifyPlanReady"
    },
    
    "NotifyPlanReady": {
      "Type": "Task",
      "Resource": "${slack_lambda_arn}",
      "Parameters": {
        "action": "notify_plan_ready",
        "taskId.$": "$.taskId",
        "ticketId.$": "$.ticketId",
        "plan.$": "$.planResult",
        "prs.$": "$.planResult.prsCreated"
      },
      "ResultPath": "$.slackNotification",
      "Next": "WaitForHumanApproval"
    },
    
    "WaitForHumanApproval": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:getItem.waitForTaskToken",
      "Parameters": {
        "TableName": "${tasks_table_name}",
        "Key": {
          "pk": {"S.$": "States.Format('TASK#{}', $.taskId)"},
          "sk": {"S": "APPROVAL"}
        },
        "TaskToken.$": "$$.Task.Token"
      },
      "ResultPath": "$.approval",
      "TimeoutSeconds": 86400,
      "Catch": [
        {
          "ErrorEquals": ["States.Timeout"],
          "Next": "ApprovalTimeout"
        }
      ],
      "Next": "CheckApprovalStatus"
    },
    
    "CheckApprovalStatus": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.approval.status",
          "StringEquals": "approved",
          "Next": "ExecuteImplementation"
        },
        {
          "Variable": "$.approval.status",
          "StringEquals": "rejected",
          "Next": "PlanRejected"
        }
      ],
      "Default": "PlanRejected"
    },
    
    "ExecuteImplementation": {
      "Type": "Task",
      "Resource": "arn:aws:states:::bedrock:invokeAgentCore",
      "Parameters": {
        "agentRuntimeEndpoint.$": "$.executionAgentEndpoint",
        "sessionId.$": "$.taskId",
        "inputText.$": "States.Format('Execute plan: {}', States.JsonToString($.planResult.plan))"
      },
      "ResultPath": "$.executionResult",
      "TimeoutSeconds": 7200,
      "Next": "MonitorCI"
    },
    
    "MonitorCI": {
      "Type": "Task",
      "Resource": "arn:aws:states:::bedrock:invokeAgentCore",
      "Parameters": {
        "agentRuntimeEndpoint.$": "$.cicdAgentEndpoint",
        "sessionId.$": "$.taskId",
        "inputText.$": "States.Format('Monitor CI for PRs: {}', States.JsonToString($.planResult.prsCreated))"
      },
      "ResultPath": "$.ciResult",
      "TimeoutSeconds": 3600,
      "Next": "CheckCIResult"
    },
    
    "CheckCIResult": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.ciResult.success",
          "BooleanEquals": true,
          "Next": "TaskComplete"
        },
        {
          "Variable": "$.ciResult.escalated",
          "BooleanEquals": true,
          "Next": "HumanInterventionRequired"
        }
      ],
      "Default": "CIFailed"
    },
    
    "TaskComplete": {
      "Type": "Task",
      "Resource": "${slack_lambda_arn}",
      "Parameters": {
        "action": "task_complete",
        "taskId.$": "$.taskId",
        "ticketId.$": "$.ticketId",
        "prs.$": "$.planResult.prsCreated"
      },
      "End": true
    },
    
    "HumanInterventionRequired": {
      "Type": "Task",
      "Resource": "${slack_lambda_arn}",
      "Parameters": {
        "action": "escalated",
        "taskId.$": "$.taskId",
        "reason.$": "$.ciResult.reason"
      },
      "End": true
    },
    
    "CIFailed": {
      "Type": "Fail",
      "Error": "CIFailed",
      "Cause": "CI pipeline failed after auto-fix attempts"
    },
    
    "ApprovalTimeout": {
      "Type": "Fail",
      "Error": "ApprovalTimeout",
      "Cause": "No approval received within 24 hours"
    },
    
    "PlanRejected": {
      "Type": "Succeed"
    },
    
    "UnknownSource": {
      "Type": "Fail",
      "Error": "UnknownSource",
      "Cause": "Unknown webhook source"
    },
    
    "SentryErrorWorkflow": {
      "Type": "Pass",
      "Comment": "Handled by Sentry Agent EventBridge rule",
      "End": true
    },
    
    "GitHubCommentWorkflow": {
      "Type": "Pass",
      "Comment": "Handle GitHub PR comment commands",
      "End": true
    }
  }
}
```

---

## 📊 Monitoring & Dashboard

### CloudWatch Dashboard

```hcl
# infrastructure/terraform/cloudwatch.tf

resource "aws_cloudwatch_dashboard" "agent_system" {
  dashboard_name = "${var.project_name}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      # Summary metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/StepFunctions", "ExecutionsStarted", {stat = "Sum", label = "Workflows Started"}],
            [".", "ExecutionsSucceeded", {stat = "Sum", label = "Workflows Succeeded"}],
            [".", "ExecutionsFailed", {stat = "Sum", label = "Workflows Failed"}]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Workflow Executions"
        }
      },
      
      # Agent invocations
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/BedrockAgentCore", "AgentInvocations", {agentName = "discovery-agent"}],
            ["...", {agentName = "planning-agent"}],
            ["...", {agentName = "execution-agent"}],
            ["...", {agentName = "cicd-agent"}]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Agent Invocations"
        }
      },
      
      # Average execution time
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/BedrockAgentCore", "AgentDuration", {agentName = "discovery-agent", stat = "Average"}],
            ["...", {agentName = "planning-agent"}],
            ["...", {agentName = "execution-agent"}]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Avg Execution Time (ms)"
        }
      },
      
      # Token usage (costs)
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Bedrock", "InputTokens", {ModelId = "anthropic.claude-sonnet-4-20250514-v1:0"}],
            [".", "OutputTokens", {ModelId = "anthropic.claude-sonnet-4-20250514-v1:0"}],
            [".", "InputTokens", {ModelId = "anthropic.claude-opus-4-20250514-v1:0"}],
            [".", "OutputTokens", {ModelId = "anthropic.claude-opus-4-20250514-v1:0"}]
          ]
          period = 3600
          stat   = "Sum"
          region = var.aws_region
          title  = "LLM Token Usage"
        }
      },
      
      # DynamoDB operations
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", {TableName = "${var.project_name}-tasks"}],
            [".", "ConsumedWriteCapacityUnits", {TableName = "${var.project_name}-tasks"}]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "DynamoDB Operations"
        }
      },
      
      # Lambda errors
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", {FunctionName = "${var.project_name}-webhook-router"}],
            ["...", {FunctionName = "${var.project_name}-slack-handler"}]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Errors"
        }
      },
      
      # Task status distribution (custom metric)
      {
        type = "metric"
        properties = {
          metrics = [
            ["AgentSystem", "TasksStarted", {Environment = var.environment}],
            [".", "TasksCompleted"],
            [".", "TasksFailed"],
            [".", "TasksEscalated"]
          ]
          period = 3600
          stat   = "Sum"
          region = var.aws_region
          title  = "Task Status Distribution"
        }
      }
    ]
  })
}

# Alarms
resource "aws_cloudwatch_metric_alarm" "high_failure_rate" {
  alarm_name          = "${var.project_name}-high-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/StepFunctions"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "More than 5 workflow failures in 10 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "agent_errors" {
  alarm_name          = "${var.project_name}-agent-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "AgentErrors"
  namespace           = "AWS/BedrockAgentCore"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Agent execution errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "slack_alerts" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.slack_alerter.arn
}
```

### Custom Metrics Publishing

```python
# Publish custom metrics from agents
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def publish_task_metric(task_status: str):
    """Publish task status metric."""
    cloudwatch.put_metric_data(
        Namespace='AgentSystem',
        MetricData=[
            {
                'MetricName': f'Tasks{task_status.capitalize()}',
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'Environment', 'Value': os.environ['ENVIRONMENT']}
                ]
            }
        ]
    )
```

---

## 🚀 Deployment Guide

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.6
3. **AWS CLI** configured
4. **GitHub Organization** with admin access
5. **Jira Cloud** instance with OAuth app
6. **Sentry** account with API token
7. **Slack** workspace with bot app

### Step 1: Setup MCP Servers

#### GitHub MCP Server

```bash
# Install GitHub MCP Server (runs on your infrastructure or use hosted)
npm install -g @modelcontextprotocol/server-github

# Start server
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
mcp-server-github --port 3000

# Or deploy to AWS Lambda/Fargate (recommended for production)
```

#### Atlassian Rovo MCP (Official)

```bash
# Set up OAuth app in Atlassian
# 1. Go to https://developer.atlassian.com/console/myapps/
# 2. Create new OAuth 2.0 integration
# 3. Add callback URL: https://your-domain.com/oauth/callback
# 4. Add scopes: read:jira-work, write:jira-work, read:jira-user
# 5. Save client ID and secret
```

#### Sentry MCP Server

```bash
# Create Sentry auth token
# 1. Go to https://sentry.io/settings/account/api/auth-tokens/
# 2. Create new token with scopes: event:read, project:read, org:read
# 3. Save token
```

### Step 2: Configure Terraform Variables

```bash
# Create terraform.tfvars
cat > infrastructure/terraform/prod.tfvars << EOF
environment = "prod"
aws_region  = "us-east-1"
project_name = "enterprise-agentcore"

# GitHub
github_org = "your-org-name"
github_token = "ghp_xxxxxxxxxxxx"
github_mcp_server_url = "https://your-mcp-server.com:3000"

# Jira
jira_base_url = "https://yourcompany.atlassian.net"
jira_oauth_client_id = "your-client-id"
jira_oauth_client_secret = "your-client-secret"

# Sentry
sentry_org = "your-sentry-org"
sentry_auth_token = "sntrys_xxxxxxxxxxxx"
sentry_mcp_server_url = "https://sentry.io/api/0/mcp"

# Slack
slack_bot_token = "xoxb-xxxxxxxxxxxx"
slack_signing_secret = "xxxxxxxxxxxx"

# Optional: Existing Knowledge Base
knowledge_base_id = ""  # Leave empty to create new
EOF
```

### Step 3: Deploy Infrastructure

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file=prod.tfvars -out=tfplan

# Review plan carefully!

# Apply
terraform apply tfplan

# Save outputs
terraform output -json > outputs.json
```

### Step 4: Deploy Agent Code

```bash
# Package agents
cd ../..

for agent in discovery planning execution cicd sentry slack; do
  cd agents/${agent}_agent
  
  # Install dependencies
  pip install -r requirements.txt -t package/
  
  # Copy code
  cp -r *.py package/
  
  # Create deployment package
  cd package
  zip -r ../deployment.zip .
  cd ..
  
  # Upload to AgentCore Runtime
  aws bedrock-agentcore update-agent-runtime \
    --agent-runtime-id $(cat ../../infrastructure/terraform/outputs.json | jq -r ".${agent}_agent_id.value") \
    --agent-source file://deployment.zip
  
  cd ../..
done
```

### Step 5: Configure Webhooks

```bash
# Get API Gateway URL
API_URL=$(cat infrastructure/terraform/outputs.json | jq -r '.api_endpoint.value')

echo "Configure webhooks:"
echo ""
echo "Jira Webhook:"
echo "  URL: ${API_URL}/webhooks/jira"
echo "  Events: Issue Created, Issue Updated"
echo ""
echo "GitHub Webhook:"
echo "  URL: ${API_URL}/webhooks/github"
echo "  Events: Pull Request, Issue Comment"
echo "  Secret: (from Secrets Manager)"
echo ""
echo "Sentry Webhook:"
echo "  URL: ${API_URL}/webhooks/sentry"
echo "  Events: Issue Alerts"
```

### Step 6: Test the System

```bash
# Create test Jira ticket with AI label
curl -X POST "https://yourcompany.atlassian.net/rest/api/3/issue" \
  -H "Authorization: Bearer ${JIRA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {"key": "PROJ"},
      "summary": "Test AI agent system",
      "description": "This is a test ticket for the AI agent system",
      "issuetype": {"name": "Task"},
      "labels": ["AI"]
    }
  }'

# Monitor execution
aws stepfunctions list-executions \
  --state-machine-arn $(cat infrastructure/terraform/outputs.json | jq -r '.state_machine_arn.value') \
  --max-results 10

# Check CloudWatch logs
aws logs tail /aws/lambda/${PROJECT_NAME}-webhook-router --follow
```

---

## 💰 Cost Analysis

### Monthly Cost Breakdown (Estimates)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **AgentCore Runtime** | 100 tasks/month, 30min avg | $0.015/min | $45 |
| **Claude Sonnet 4.5** | 5M input + 500K output tokens | $3/$15 per MTok | $22.50 |
| **Claude Opus 4.5** | 2M input + 200K output tokens | $15/$75 per MTok | $45 |
| **DynamoDB** | 10K reads, 5K writes/day | On-demand | $5 |
| **S3** | 10GB storage + transfers | $0.023/GB | $1 |
| **API Gateway** | 50K requests/month | $1/million | $0.05 |
| **Lambda** | 100K invocations, 256MB | Free tier | $0 |
| **CloudWatch** | Logs + metrics | Standard pricing | $10 |
| **Secrets Manager** | 6 secrets | $0.40/secret | $2.40 |
| **Step Functions** | 100 workflows/month | $0.025/1K transitions | $5 |
| | | **TOTAL** | **~$136/month** |

### Cost Optimization Tips

1. **Use Haiku for simple tasks** - 10x cheaper than Sonnet
2. **Enable DynamoDB auto-scaling** - Only pay for what you use
3. **Set Lambda reserved concurrency** - Avoid runaway costs
4. **Archive old S3 artifacts** - Lifecycle policies to Glacier
5. **Use CloudWatch Logs Insights** - Query instead of exporting
6. **Monitor token usage** - Alert on unusual spikes

### Cost by Team Size

| Team Size | Tasks/Month | Estimated Cost |
|-----------|-------------|----------------|
| Small (5-10 devs) | 50 | $80 |
| Medium (10-30 devs) | 150 | $200 |
| Large (30-100 devs) | 500 | $600 |

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Agent Not Responding

**Symptoms:**
- Step Functions execution stuck
- No logs in CloudWatch

**Solutions:**
```bash
# Check agent runtime status
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-id <runtime-id>

# View agent logs
aws logs tail /aws/bedrock-agentcore/<agent-name> --follow

# Restart runtime
aws bedrock-agentcore update-agent-runtime \
  --agent-runtime-id <runtime-id> \
  --restart true
```

#### 2. MCP Connection Failed

**Symptoms:**
- "Gateway timeout" errors
- Tool invocations failing

**Solutions:**
```bash
# Test MCP server connectivity
curl -X POST https://your-mcp-server.com/health

# Check gateway configuration
aws bedrock-agentcore describe-gateway \
  --gateway-id <gateway-id>

# Verify secrets
aws secretsmanager get-secret-value \
  --secret-id <secret-arn>
```

#### 3. High Costs

**Symptoms:**
- Unexpected AWS bill
- CloudWatch cost alarms

**Solutions:**
```bash
# Check token usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokens \
  --dimensions Name=ModelId,Value=anthropic.claude-opus-4-20250514-v1:0 \
  --start-time 2026-01-01T00:00:00Z \
  --end-time 2026-01-31T23:59:59Z \
  --period 86400 \
  --statistics Sum

# Review long-running executions
aws stepfunctions list-executions \
  --state-machine-arn <arn> \
  --status-filter RUNNING \
  --max-results 100

# Set budget alerts
aws budgets create-budget \
  --account-id <account-id> \
  --budget file://budget.json
```

---

## 📚 Additional Resources

- [AWS Bedrock AgentCore Documentation](https://aws.amazon.com/bedrock/agentcore/)
- [Model Context Protocol Spec](https://github.com/modelcontextprotocol/specification)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Atlassian Rovo MCP](https://support.atlassian.com/atlassian-rovo-mcp-server/)
- [Sentry MCP](https://docs.sentry.io/product/sentry-mcp/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

## ✅ Success Criteria

Your system is successfully deployed when:

- [ ] All 6 agents are running and healthy
- [ ] Webhooks from Jira, GitHub, and Sentry are received
- [ ] A test Jira ticket with "AI" label triggers the full workflow
- [ ] Agents successfully discover repositories
- [ ] Planning agent creates PR with PLAN.md
- [ ] Slack notifications are received
- [ ] CloudWatch dashboard shows metrics
- [ ] Costs are within expected range

---

## 🎯 Next Steps

1. **Customize Agents** - Tune prompts for your organization
2. **Add More Integrations** - Connect to Linear, Notion, etc.
3. **Enhance Knowledge Base** - Feed past solutions for better recommendations
4. **A/B Test Models** - Compare Sonnet vs Opus performance
5. **Scale Testing** - Load test with 100+ concurrent tasks
6. **Security Audit** - Review IAM policies, enable GuardDuty
7. **Team Training** - Train developers on using the system

---

**Document Version:** 2.0  
**Last Updated:** January 17, 2026  
**Maintained By:** Enterprise AI Team  

For questions or issues, contact: #ai-agents Slack channel

