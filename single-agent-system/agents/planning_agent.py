"""
Planning Agent Implementation
=============================
Creates implementation plans with TDD approach.
Mirrors the distributed system's planning_agent/main.py
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import structlog
from langchain_aws import ChatBedrock

from config import settings

logger = structlog.get_logger(__name__)


class PlanningAgent:
    """Agent for creating implementation plans."""
    
    def __init__(self, mcp_gateway):
        """Initialize the planning agent."""
        self.llm = ChatBedrock(
            model_id=settings.bedrock.planning_model,
            region_name=settings.aws.region,
            model_kwargs={
                "max_tokens": settings.bedrock.max_tokens,
                "temperature": settings.bedrock.temperature
            }
        )
        self.jira_mcp = mcp_gateway.get_tool("jira-mcp")
        self.github_mcp = mcp_gateway.get_tool("github-mcp")
        self.code_interpreter = mcp_gateway.get_service("code-interpreter")
        
        self._load_prompts()
        logger.info("planning_agent_initialized", model=settings.bedrock.planning_model)
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "planning"
        
        system_prompt_path = prompts_dir / "system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text()
        else:
            self.system_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        return """You are the Planning Agent for an enterprise software organization.
Your mission is to create production-ready implementation plans following TDD principles."""
    
    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        """Call the Bedrock LLM."""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content
    
    def _parse_json(self, response: str) -> Any:
        """Parse JSON from LLM response."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {}
    
    def fetch_ticket_details(self, ticket_id: str) -> Dict[str, Any]:
        """Get full Jira ticket with all fields."""
        return self.jira_mcp.get_issue(ticket_id) or {}
    
    def define_scope(self, ticket: Dict, discovery_results: Dict) -> Dict[str, List[str]]:
        """Define what's in scope and what's not."""
        prompt = f"""Based on this ticket and discovery results, define the scope:

Ticket: {json.dumps(ticket)}
Discovery: {json.dumps(discovery_results)}

Return JSON:
{{
  "inScope": ["specific item 1", "specific item 2"],
  "outOfScope": ["future work 1", "not included"]
}}"""

        response = self._call_llm(prompt)
        return self._parse_json(response) or {"inScope": [], "outOfScope": []}
    
    def design_architecture(self, scope: Dict, discovery_results: Dict) -> Dict[str, Any]:
        """Design the technical solution."""
        prompt = f"""Design architecture for this feature:

Scope: {json.dumps(scope)}
Repos: {[r['name'] for r in discovery_results.get('relevantRepos', [])[:3]]}

Return JSON:
{{
  "components": [
    {{"name": "Name", "path": "src/path", "responsibilities": ["what it does"]}}
  ],
  "dataFlow": "Description of how data moves"
}}"""

        response = self._call_llm(prompt)
        return self._parse_json(response) or {"components": [], "dataFlow": ""}
    
    def create_test_plan(self, architecture: Dict) -> Dict[str, List[Dict]]:
        """Create comprehensive test plan (TDD)."""
        prompt = f"""Create test plan for this implementation:

Architecture: {json.dumps(architecture)}
Test frameworks: {json.dumps(settings.conventions.test_frameworks)}

Return JSON:
{{
  "unitTests": [
    {{"description": "Test case", "file": "tests/test_x.py"}}
  ],
  "integrationTests": [
    {{"description": "Integration test", "file": "tests/integration/test_x.py"}}
  ]
}}"""

        response = self._call_llm(prompt)
        return self._parse_json(response) or {"unitTests": [], "integrationTests": []}
    
    def break_down_tasks(self, architecture: Dict, test_plan: Dict) -> List[Dict]:
        """Break work into granular tasks."""
        prompt = f"""Break down implementation into tasks:

Architecture: {json.dumps(architecture)}
Tests: {json.dumps(test_plan)}

Return JSON:
{{
  "tasks": [
    {{"id": 1, "description": "Write unit tests for X", "file": "path", "estimatedHours": 2, "dependencies": []}}
  ]
}}"""

        response = self._call_llm(prompt)
        result = self._parse_json(response)
        return result.get("tasks", [])
    
    def create_plan_document(self, ticket: Dict, scope: Dict, architecture: Dict, 
                             test_plan: Dict, tasks: List[Dict]) -> str:
        """Generate PLAN.md file."""
        in_scope = "\n".join(f"- ✅ {item}" for item in scope.get("inScope", []))
        out_scope = "\n".join(f"- ❌ {item}" for item in scope.get("outOfScope", []))
        
        components = ""
        for comp in architecture.get("components", []):
            responsibilities = ", ".join(comp.get("responsibilities", []))
            components += f"| {comp['name']} | `{comp['path']}` | {responsibilities} |\n"
        
        unit_tests = "\n".join(f"- [ ] {t['description']}" for t in test_plan.get("unitTests", []))
        int_tests = "\n".join(f"- [ ] {t['description']}" for t in test_plan.get("integrationTests", []))
        
        tasks_md = ""
        for t in tasks:
            deps = ", ".join(str(d) for d in t.get("dependencies", [])) or "-"
            tasks_md += f"| {t['id']} | {t['description']} | {deps} | {t.get('estimatedHours', 0)} |\n"
        
        total_hours = sum(t.get("estimatedHours", 0) for t in tasks)
        ticket_id = ticket.get("key", ticket.get("id", "UNKNOWN"))
        
        return f"""# {ticket_id}: {ticket.get('summary', 'Implementation Plan')}

## Summary
{ticket.get('description', '')[:300]}

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
{architecture.get('dataFlow', 'TBD')}

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
*Ticket: {ticket_id}*
*Generated: {datetime.utcnow().isoformat()}*
"""
    
    def create_github_pr(self, ticket: Dict, plan_md: str, discovery_results: Dict) -> List[Dict]:
        """Create branch and PR with PLAN.md."""
        prs = []
        ticket_id = ticket.get("key", ticket.get("id", "UNKNOWN"))
        
        for repo in discovery_results.get("relevantRepos", [])[:3]:
            branch_name = settings.conventions.format_branch_name(
                ticket_id=ticket_id,
                slug=ticket.get("summary", "feature")[:30]
            )
            
            # Create branch
            if self.github_mcp.create_branch(repo["name"], branch_name):
                # Add PLAN.md
                self.github_mcp.create_or_update_file(
                    repo_name=repo["name"],
                    path="PLAN.md",
                    content=plan_md,
                    message=f"feat: Add implementation plan for {ticket_id}",
                    branch=branch_name
                )
                
                # Create PR
                pr = self.github_mcp.create_pull_request(
                    repo_name=repo["name"],
                    title=f"{ticket_id}: {ticket.get('summary', 'Feature')}",
                    body=f"## Jira Ticket\n{ticket_id}\n\n## Plan\nSee PLAN.md\n\n*Created by AI Planning Agent*",
                    head=branch_name,
                    draft=True
                )
                
                if pr:
                    prs.append({
                        "repo": repo["name"],
                        "branch": branch_name,
                        "prNumber": pr["number"],
                        "prUrl": pr["html_url"]
                    })
        
        return prs
    
    def update_jira(self, ticket_id: str, discovery_results: Dict, tasks: List[Dict], 
                    test_plan: Dict, prs: List[Dict]):
        """Add comment to Jira with plan summary."""
        pr_links = "\n".join(f"- [{pr['repo']}#{pr['prNumber']}]({pr['prUrl']})" for pr in prs)
        
        comment = f"""🤖 **AI Agent: Plan Created**

📊 **Discovery Results:**
- Found {len(discovery_results.get('relevantRepos', []))} relevant repositories
- Estimated complexity: {discovery_results.get('estimatedComplexity', 'Medium')}

📋 **Plan Summary:**
- Tasks: {len(tasks)}
- Estimated hours: {sum(t.get('estimatedHours', 0) for t in tasks)}
- Test cases: {len(test_plan.get('unitTests', []))}

🔗 **Pull Requests:**
{pr_links}

⏭️ **Next Step:** Team review and approval via Slack
"""
        
        self.jira_mcp.add_comment(ticket_id, comment)
    
    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run planning for a ticket.
        
        Args:
            request: Contains ticketId, discoveryResults
            
        Returns:
            PlanningResult dict
        """
        ticket_id = request.get("ticketId")
        discovery_results = request.get("discoveryResults", {})
        
        logger.info("planning_started", ticket_id=ticket_id)
        
        # Fetch ticket details
        ticket = self.fetch_ticket_details(ticket_id) if ticket_id else request.get("ticket", {})
        
        # Define scope
        scope = self.define_scope(ticket, discovery_results)
        logger.info("scope_defined")
        
        # Design architecture
        architecture = self.design_architecture(scope, discovery_results)
        logger.info("architecture_designed")
        
        # Create test plan (TDD - tests first!)
        test_plan = self.create_test_plan(architecture)
        logger.info("test_plan_created")
        
        # Break down tasks
        tasks = self.break_down_tasks(architecture, test_plan)
        logger.info("tasks_created", count=len(tasks))
        
        # Generate plan document
        plan_md = self.create_plan_document(ticket, scope, architecture, test_plan, tasks)
        
        # Save plan locally
        output_dir = settings.execution.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        plan_path = output_dir / f"{ticket_id or 'LOCAL'}_PLAN.md"
        plan_path.write_text(plan_md)
        logger.info("plan_saved", path=str(plan_path))
        
        # Create GitHub PRs (if not dry run)
        prs = []
        if not settings.execution.dry_run:
            prs = self.create_github_pr(ticket, plan_md, discovery_results)
            if prs and ticket_id:
                self.update_jira(ticket_id, discovery_results, tasks, test_plan, prs)
        
        result = {
            "plan": {
                "scope": scope,
                "architecture": architecture,
                "testStrategy": test_plan,
                "implementation": {"tasks": tasks}
            },
            "prsCreated": prs,
            "planMarkdown": plan_md,
            "totalEstimatedHours": sum(t.get("estimatedHours", 0) for t in tasks)
        }
        
        logger.info("planning_complete", tasks=len(tasks), prs=len(prs))
        return result
