"""
Local Runner for Multiple-Agents System
========================================
Runs the distributed agent workflow locally using AWS Bedrock + AgentCore.
Same gateway as cloud - requires AWS credentials.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from dotenv import load_dotenv

load_dotenv()

from agents.shared.gateway import AgentCoreGateway

logger = structlog.get_logger(__name__)


class LocalTaskStore:
    """In-memory task storage (matches DynamoDB interface for local testing)."""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
    
    def put_item(self, item: Dict[str, Any]):
        pk = item.get("pk", "")
        sk = item.get("sk", "")
        self._tasks[f"{pk}#{sk}"] = item
    
    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(f"{pk}#{sk}")
    
    def update_item(self, pk: str, sk: str, updates: Dict[str, Any]):
        key = f"{pk}#{sk}"
        if key in self._tasks:
            self._tasks[key].update(updates)
        else:
            self._tasks[key] = {"pk": pk, "sk": sk, **updates}
    
    def scan(self, filter_status: Optional[str] = None) -> list:
        items = list(self._tasks.values())
        if filter_status:
            items = [i for i in items if i.get("status") == filter_status]
        return items


class LocalAgentOrchestrator:
    """
    Orchestrates the complete agent workflow locally.
    
    Uses the same AgentCoreGateway as the cloud Lambda functions,
    but runs all agents in a single process for testing.
    """
    
    def __init__(self):
        self.gateway = AgentCoreGateway()
        self.task_store = LocalTaskStore()
        
        # Initialize agents (lazy loaded)
        self._agents_initialized = False
        self.discovery = None
        self.planning = None
        self.execution = None
        self.cicd = None
        self.sentry = None
        self.slack = None
        
        logger.info("local_orchestrator_initialized")
    
    def _init_agents(self):
        """Initialize all agents (lazy)."""
        if self._agents_initialized:
            return
        
        from agents.discovery_agent.main import DiscoveryAgent
        from agents.planning_agent.main import PlanningAgent
        from agents.execution_agent.main import ExecutionAgent
        from agents.cicd_agent.main import CICDAgent
        from agents.sentry_agent.main import SentryAgent
        from agents.slack_agent.main import SlackAgent
        
        self.discovery = DiscoveryAgent(self.gateway)
        self.planning = PlanningAgent(self.gateway)
        self.execution = ExecutionAgent(self.gateway)
        self.cicd = CICDAgent(self.gateway)
        self.sentry = SentryAgent(self.gateway)
        self.slack = SlackAgent(self.gateway)
        
        self._agents_initialized = True
    
    def run_full_workflow(self, ticket: Dict[str, Any], auto_approve: bool = True) -> Dict[str, Any]:
        """Run the complete workflow for a ticket.
        
        Args:
            ticket: Ticket data (id, summary, description)
            auto_approve: If True, skip waiting for approval
            
        Returns:
            Complete workflow result
        """
        self._init_agents()
        
        task_id = f"local-{ticket.get('id', 'unknown')}-{int(datetime.utcnow().timestamp())}"
        ticket_id = ticket.get("id") or ticket.get("key", "LOCAL")
        
        logger.info("workflow_started", task_id=task_id, ticket_id=ticket_id)
        
        # Store task
        self._update_task(task_id, {
            "task_id": task_id,
            "ticket_id": ticket_id,
            "status": "started",
            "source": "local",
            "created_at": datetime.utcnow().isoformat()
        })
        
        result = {
            "taskId": task_id,
            "ticketId": ticket_id,
            "phases": {},
            "success": False,
            "error": None
        }
        
        try:
            # PHASE 1: DISCOVERY
            self._update_task(task_id, {"status": "discovery", "current_agent": "Discovery"})
            logger.info("phase_discovery_started", task_id=task_id)
            
            discovery_result = self.discovery.run(ticket)
            result["phases"]["discovery"] = discovery_result
            
            # PHASE 2: PLANNING
            self._update_task(task_id, {"status": "planning", "current_agent": "Planning", "progress": 25})
            logger.info("phase_planning_started", task_id=task_id)
            
            planning_result = self.planning.run({
                "ticketId": ticket_id,
                "ticket": ticket,
                "discoveryResults": discovery_result
            })
            result["phases"]["planning"] = planning_result
            
            # PHASE 3: APPROVAL
            self._update_task(task_id, {"status": "awaiting_approval", "progress": 40})
            
            if not auto_approve:
                result["phases"]["approval"] = {"status": "pending"}
                result["awaitingApproval"] = True
                return result
            
            self._update_task(task_id, {"status": "approved"})
            
            # PHASE 4: EXECUTION
            self._update_task(task_id, {"status": "executing", "current_agent": "Execution", "progress": 50})
            logger.info("phase_execution_started", task_id=task_id)
            
            execution_result = self.execution.run({
                "plan": planning_result.get("plan", {}),
                "prInfo": planning_result.get("prsCreated", [{}])[0] if planning_result.get("prsCreated") else {}
            })
            result["phases"]["execution"] = execution_result
            
            # PHASE 5: CI/CD
            self._update_task(task_id, {"status": "ci_monitoring", "current_agent": "CI/CD", "progress": 80})
            
            if planning_result.get("prsCreated"):
                pr_info = planning_result["prsCreated"][0]
                cicd_result = self.cicd.run({
                    "repo": pr_info["repo"],
                    "prNumber": pr_info["prNumber"]
                })
                result["phases"]["cicd"] = cicd_result
            else:
                result["phases"]["cicd"] = {"skipped": True, "reason": "No PRs created"}
            
            # COMPLETE
            self._update_task(task_id, {"status": "completed", "progress": 100})
            result["success"] = True
            logger.info("workflow_completed", task_id=task_id, success=True)
            
        except Exception as e:
            logger.error("workflow_failed", task_id=task_id, error=str(e))
            self._update_task(task_id, {"status": "failed", "error": str(e)})
            result["error"] = str(e)
            result["success"] = False
        
        return result
    
    def run_from_jira(self, ticket_key: str, auto_approve: bool = True) -> Dict[str, Any]:
        """Run workflow for a Jira ticket by key."""
        jira = self.gateway.get_tool("jira-mcp")
        ticket = jira.get_issue(ticket_key)
        
        if not ticket:
            raise ValueError(f"Ticket not found: {ticket_key}")
        
        return self.run_full_workflow({
            "id": ticket["key"],
            "key": ticket["key"],
            "summary": ticket["summary"],
            "description": ticket["description"],
            "labels": ticket.get("labels", []),
            "priority": ticket.get("priority", "Medium")
        }, auto_approve=auto_approve)
    
    def run_from_description(self, description: str, title: Optional[str] = None,
                             auto_approve: bool = True) -> Dict[str, Any]:
        """Run workflow from a text description."""
        return self.run_full_workflow({
            "id": f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "summary": title or description[:100],
            "description": description,
            "labels": [],
            "priority": "Medium"
        }, auto_approve=auto_approve)
    
    def run_sentry_monitoring(self) -> Dict[str, Any]:
        """Run Sentry error monitoring."""
        self._init_agents()
        logger.info("sentry_monitoring_triggered")
        return self.sentry.run()
    
    def handle_slack_command(self, command: str, args: list, user_id: str = "local") -> str:
        """Handle a Slack slash command."""
        self._init_agents()
        return self.slack.handle_command(command, args, user_id)
    
    def _update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update task in local store."""
        updates["last_update"] = datetime.utcnow().isoformat()
        self.task_store.update_item(f"TASK#{task_id}", "METADATA", updates)


def get_orchestrator() -> LocalAgentOrchestrator:
    """Get orchestrator instance."""
    return LocalAgentOrchestrator()
