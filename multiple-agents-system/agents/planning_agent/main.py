"""
Planning Agent Implementation
=============================
Creates implementation plans with TDD approach.
"""

import json
import os
from typing import TypedDict, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import settings


class PlanningState(TypedDict):
    """State for the planning workflow."""
    ticketId: str
    ticketDetails: dict
    discoveryResults: dict
    conventions: dict
    scope: dict
    architecture: dict
    testPlan: dict
    tasks: List[dict]
    planMarkdown: str
    prsCreated: List[dict]


class PlanningAgent:
    """Agent for creating implementation plans."""
    
    def __init__(self, agentcore_gateway):
        """Initialize the planning agent."""
        self.llm = ChatBedrock(
            model_id=settings.models.planning_model,
            region_name=settings.aws.region
        )
        self.jira_mcp = agentcore_gateway.get_tool("jira-mcp")
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.code_interpreter = agentcore_gateway.get_service("code-interpreter")
        
        self._load_prompts()
        self.graph = self._build_graph()
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "planning"
        )
        
        with open(os.path.join(prompts_dir, "system.md")) as f:
            self.system_prompt = f.read()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
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
    
    async def fetch_ticket_details(self, state: PlanningState) -> PlanningState:
        """Get full Jira ticket with all fields."""
        ticket = await self.jira_mcp.get_issue(
            issue_key=state["ticketId"]
        )
        
        related = await self.jira_mcp.search_issues(
            jql=f"issue in linkedIssues({state['ticketId']})"
        )
        
        return {
            **state,
            "ticketDetails": ticket,
            "relatedTickets": related
        }
    
    async def define_scope(self, state: PlanningState) -> PlanningState:
        """Define what's in scope and what's not."""
        prompt = f"""
        Based on this ticket and discovery results, define the scope:
        
        Ticket: {json.dumps(state['ticketDetails'])}
        Discovery: {json.dumps(state['discoveryResults'])}
        
        Return JSON:
        {{
          "inScope": ["specific item 1", "specific item 2"],
          "outOfScope": ["future work 1", "not included"]
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        scope = json.loads(response.content)
        
        return {**state, "scope": scope}
    
    async def design_architecture(self, state: PlanningState) -> PlanningState:
        """Design the technical solution."""
        existing_code_samples = []
        for repo in state["discoveryResults"].get("relevantRepos", [])[:2]:
            for file in repo.get("files", [])[:3]:
                content = await self.github_mcp.get_file(
                    repo=repo["name"],
                    path=file["path"]
                )
                existing_code_samples.append({
                    "file": file["path"],
                    "content": content[:1000]
                })
        
        prompt = f"""
        Design architecture for this feature:
        
        Scope: {json.dumps(state['scope'])}
        Existing code patterns: {json.dumps(existing_code_samples)}
        
        Return JSON:
        {{
          "components": [
            {{"name": "Name", "path": "src/path", "responsibilities": ["what it does"]}}
          ],
          "dataFlow": "Description of how data moves"
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        architecture = json.loads(response.content)
        
        return {**state, "architecture": architecture}
    
    async def create_test_plan(self, state: PlanningState) -> PlanningState:
        """Create comprehensive test plan (TDD)."""
        prompt = f"""
        Create test plan for this implementation:
        
        Architecture: {json.dumps(state['architecture'])}
        Test frameworks: {json.dumps(settings.conventions.test_frameworks)}
        
        Return JSON:
        {{
          "unitTests": [
            {{"description": "Test case", "file": "tests/test_x.py"}}
          ],
          "integrationTests": [
            {{"description": "Integration test", "file": "tests/integration/test_x.py"}}
          ]
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        test_plan = json.loads(response.content)
        
        return {**state, "testPlan": test_plan}
    
    async def break_down_tasks(self, state: PlanningState) -> PlanningState:
        """Break work into granular tasks."""
        prompt = f"""
        Break down implementation into tasks:
        
        Architecture: {json.dumps(state['architecture'])}
        Tests: {json.dumps(state['testPlan'])}
        
        Return JSON:
        {{
          "tasks": [
            {{"id": 1, "description": "Write unit tests for X", "file": "path", "estimatedHours": 2, "dependencies": []}}
          ]
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        tasks_data = json.loads(response.content)
        
        return {**state, "tasks": tasks_data.get("tasks", [])}
    
    async def create_plan_document(self, state: PlanningState) -> PlanningState:
        """Generate PLAN.md file."""
        in_scope = "\n".join(f"- ✅ {item}" for item in state['scope'].get('inScope', []))
        out_scope = "\n".join(f"- ❌ {item}" for item in state['scope'].get('outOfScope', []))
        
        components = ""
        for comp in state['architecture'].get('components', []):
            components += f"| {comp['name']} | `{comp['path']}` | {', '.join(comp.get('responsibilities', []))} |\n"
        
        unit_tests = "\n".join(f"- [ ] {t['description']}" for t in state['testPlan'].get('unitTests', []))
        int_tests = "\n".join(f"- [ ] {t['description']}" for t in state['testPlan'].get('integrationTests', []))
        
        tasks_md = ""
        for t in state['tasks']:
            deps = ", ".join(str(d) for d in t.get('dependencies', [])) or "-"
            tasks_md += f"| {t['id']} | {t['description']} | {deps} | {t['estimatedHours']} |\n"
        
        total_hours = sum(t.get('estimatedHours', 0) for t in state['tasks'])
        
        plan_md = f"""# {state['ticketId']}: {state['ticketDetails'].get('summary', 'Implementation Plan')}

## Summary
{state['ticketDetails'].get('description', '')[:300]}

## Scope

### In Scope
{in_scope}

### Out of Scope
{out_scope}

## Architecture

### Components
| Component | Path | Responsibility |
|-----------|------|----------------|
{components}

### Data Flow
{state['architecture'].get('dataFlow', 'TBD')}

## Test Plan

### Unit Tests
{unit_tests}

### Integration Tests
{int_tests}

## Implementation Tasks

| # | Task | Dependencies | Est. Hours |
|---|------|--------------|------------|
{tasks_md}

**Total Estimated Hours:** {total_hours}

## Security Considerations
- [ ] Input validation
- [ ] Authentication/Authorization
- [ ] Data encryption

## Rollback Plan
Revert the changes if issues are detected.

---
*Generated by AI Planning Agent*
*Ticket: {state['ticketId']}*
*Generated: {datetime.utcnow().isoformat()}*
"""
        
        return {**state, "planMarkdown": plan_md}
    
    async def create_github_pr(self, state: PlanningState) -> PlanningState:
        """Create branch and PR with PLAN.md."""
        prs = []
        
        for repo in state["discoveryResults"].get("relevantRepos", [])[:3]:
            branch_name = settings.conventions.format_branch_name(
                ticket_id=state["ticketId"],
                slug=state["ticketDetails"].get("summary", "feature")[:30]
            )
            
            await self.github_mcp.create_branch(
                repo=repo["name"],
                branch=branch_name,
                from_branch="main"
            )
            
            await self.github_mcp.create_or_update_file(
                repo=repo["name"],
                path="PLAN.md",
                content=state["planMarkdown"],
                message=f"feat: Add implementation plan for {state['ticketId']}",
                branch=branch_name
            )
            
            pr = await self.github_mcp.create_pull_request(
                repo=repo["name"],
                title=f"{state['ticketId']}: {state['ticketDetails'].get('summary', 'Feature')}",
                head=branch_name,
                base="main",
                body=f"## Jira Ticket\n{state['ticketId']}\n\n## Plan\nSee PLAN.md\n\n*Created by AI Planning Agent*",
                draft=True
            )
            
            prs.append({
                "repo": repo["name"],
                "branch": branch_name,
                "prNumber": pr["number"],
                "prUrl": pr["html_url"]
            })
        
        return {**state, "prsCreated": prs}
    
    async def update_jira(self, state: PlanningState) -> PlanningState:
        """Add comment to Jira with plan summary."""
        pr_links = "\n".join(f"- [{pr['repo']}#{pr['prNumber']}]({pr['prUrl']})" for pr in state['prsCreated'])
        
        comment = f"""🤖 **AI Agent: Plan Created**

📊 **Discovery Results:**
- Found {len(state['discoveryResults'].get('relevantRepos', []))} relevant repositories
- Estimated complexity: {state['discoveryResults'].get('estimatedComplexity', 'Medium')}

📋 **Plan Summary:**
- Tasks: {len(state['tasks'])}
- Estimated hours: {sum(t.get('estimatedHours', 0) for t in state['tasks'])}
- Test cases: {len(state['testPlan'].get('unitTests', []))}

🔗 **Pull Requests:**
{pr_links}

⏭️ **Next Step:** Team review and approval via Slack
"""
        
        await self.jira_mcp.add_comment(
            issue_key=state["ticketId"],
            comment=comment
        )
        
        return state
    
    async def run(self, request: dict) -> dict:
        """Run planning for a ticket."""
        initial_state = {
            "ticketId": request["ticketId"],
            "ticketDetails": request.get("ticketDetails", {}),
            "discoveryResults": request.get("discoveryResults", {}),
            "conventions": {
                "branchNaming": settings.conventions.branch_naming_pattern,
                "testFrameworks": settings.conventions.test_frameworks
            },
            "scope": {},
            "architecture": {},
            "testPlan": {},
            "tasks": [],
            "planMarkdown": "",
            "prsCreated": []
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "plan": {
                "scope": final_state["scope"],
                "architecture": final_state["architecture"],
                "testStrategy": final_state["testPlan"],
                "implementation": {"tasks": final_state["tasks"]}
            },
            "prsCreated": final_state["prsCreated"]
        }


async def handler(event, context):
    """Lambda handler for planning agent."""
    from agents.shared.gateway import AgentCoreGateway
    
    gateway = AgentCoreGateway()
    agent = PlanningAgent(gateway)
    
    result = await agent.run(event)
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
