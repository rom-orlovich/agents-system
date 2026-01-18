"""
Agent Orchestrator
==================
Orchestrates the complete workflow: Discovery → Planning → Approval → Execution → Verification → CI/CD
Mirrors Step Functions workflow from the distributed system but runs locally in one process.
"""

from datetime import datetime
from typing import Dict, Any, Optional

import structlog

from config import settings
from mcp import get_gateway
from .discovery_agent import DiscoveryAgent
from .planning_agent import PlanningAgent
from .execution_agent import ExecutionAgent
from .cicd_agent import CICDAgent
from .sentry_agent import SentryAgent
from .slack_agent import SlackAgent

logger = structlog.get_logger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the complete agent workflow.
    
    This mirrors the AWS Step Functions state machine from the distributed system,
    running all agents in sequence with the same flow:
    
    1. Discovery Agent  → Find relevant repos
    2. Planning Agent   → Create implementation plan
    3. Slack Agent      → Notify for approval (simulated locally)
    4. Execution Agent  → Implement code
    5. CI/CD Agent      → Monitor pipeline
    6. Slack Agent      → Notify completion
    """
    
    def __init__(self):
        """Initialize the orchestrator with all agents."""
        self.gateway = get_gateway()
        
        # Initialize all agents
        self.discovery = DiscoveryAgent(self.gateway)
        self.planning = PlanningAgent(self.gateway)
        self.execution = ExecutionAgent(self.gateway)
        self.cicd = CICDAgent(self.gateway)
        self.sentry = SentryAgent(self.gateway)
        self.slack = SlackAgent(self.gateway)
        
        self.task_store = self.gateway.get_task_store()
        
        logger.info("orchestrator_initialized")
    
    def run_full_workflow(self, ticket: Dict[str, Any], auto_approve: bool = True) -> Dict[str, Any]:
        """Run the complete workflow for a ticket.
        
        This simulates the Step Functions state machine:
        Jira Webhook → Discovery → Planning → [Wait for Approval] → Execution → CI/CD → Complete
        
        Args:
            ticket: Ticket data (id, summary, description)
            auto_approve: If True, skip waiting for approval (for local testing)
            
        Returns:
            Complete workflow result
        """
        task_id = f"local-{ticket.get('id', 'unknown')}-{int(datetime.utcnow().timestamp())}"
        ticket_id = ticket.get("id") or ticket.get("key", "LOCAL")
        
        logger.info("workflow_started", task_id=task_id, ticket_id=ticket_id)
        
        # Store task
        self._update_task(task_id, {
            "task_id": task_id,
            "ticket_id": ticket_id,
            "status": "started",
            "source": "local",
            "created_at": datetime.utcnow().isoformat(),
            "ticket_summary": ticket.get("summary", ""),
            "ticket_description": ticket.get("description", "")
        })
        
        result = {
            "taskId": task_id,
            "ticketId": ticket_id,
            "phases": {},
            "success": False,
            "error": None
        }
        
        try:
            # ================================================================
            # PHASE 1: DISCOVERY
            # ================================================================
            self._update_task(task_id, {"status": "discovery", "current_agent": "Discovery"})
            logger.info("phase_discovery_started", task_id=task_id)
            
            discovery_result = self.discovery.run(ticket)
            result["phases"]["discovery"] = discovery_result
            
            logger.info("phase_discovery_complete", repos=len(discovery_result.get("relevantRepos", [])))
            
            # ================================================================
            # PHASE 2: PLANNING
            # ================================================================
            self._update_task(task_id, {"status": "planning", "current_agent": "Planning", "progress": 25})
            logger.info("phase_planning_started", task_id=task_id)
            
            planning_result = self.planning.run({
                "ticketId": ticket_id,
                "ticket": ticket,
                "discoveryResults": discovery_result
            })
            result["phases"]["planning"] = planning_result
            
            logger.info("phase_planning_complete", tasks=len(planning_result.get("plan", {}).get("implementation", {}).get("tasks", [])))
            
            # ================================================================
            # PHASE 3: APPROVAL (simulated for local testing)
            # ================================================================
            self._update_task(task_id, {"status": "awaiting_approval", "progress": 40})
            
            if not auto_approve:
                # In distributed system, this would wait for Slack approval
                # For local testing, we simulate approval
                self.slack.send_notification("plan_ready", {
                    "title": f"Plan ready for {ticket_id}",
                    "description": f"Tasks: {len(planning_result.get('plan', {}).get('implementation', {}).get('tasks', []))}",
                    "ticket_id": ticket_id,
                    "pr_url": planning_result.get("prsCreated", [{}])[0].get("prUrl") if planning_result.get("prsCreated") else None
                })
                
                logger.info("awaiting_approval", task_id=task_id)
                result["phases"]["approval"] = {"status": "pending", "message": "Waiting for approval"}
                result["awaitingApproval"] = True
                return result
            
            self._update_task(task_id, {"status": "approved", "approved_at": datetime.utcnow().isoformat()})
            logger.info("auto_approved", task_id=task_id)
            
            # ================================================================
            # PHASE 4: EXECUTION
            # ================================================================
            self._update_task(task_id, {"status": "executing", "current_agent": "Execution", "progress": 50})
            logger.info("phase_execution_started", task_id=task_id)
            
            execution_result = self.execution.run({
                "plan": planning_result.get("plan", {}),
                "prInfo": planning_result.get("prsCreated", [{}])[0] if planning_result.get("prsCreated") else {}
            })
            result["phases"]["execution"] = execution_result
            
            logger.info("phase_execution_complete", 
                       completed=len(execution_result.get("completedTasks", [])),
                       failed=len(execution_result.get("failedTasks", [])))
            
            # ================================================================
            # PHASE 5: CI/CD MONITORING (simulated for local)
            # ================================================================
            self._update_task(task_id, {"status": "ci_monitoring", "current_agent": "CI/CD", "progress": 80})
            
            # CI/CD monitoring would normally wait for GitHub Actions
            # For local testing, we skip if no PRs were created
            if planning_result.get("prsCreated"):
                pr_info = planning_result["prsCreated"][0]
                cicd_result = self.cicd.run({
                    "repo": pr_info["repo"],
                    "prNumber": pr_info["prNumber"]
                })
                result["phases"]["cicd"] = cicd_result
            else:
                result["phases"]["cicd"] = {"skipped": True, "reason": "No PRs created (dry run or local mode)"}
            
            # ================================================================
            # PHASE 6: COMPLETION
            # ================================================================
            self._update_task(task_id, {"status": "completed", "progress": 100})
            
            # Notify completion
            self.slack.send_notification("task_complete", {
                "summary": ticket.get("summary", ""),
                "ticket_id": ticket_id,
                "pr_url": planning_result.get("prsCreated", [{}])[0].get("prUrl") if planning_result.get("prsCreated") else None
            })
            
            result["success"] = True
            logger.info("workflow_completed", task_id=task_id, success=True)
            
        except Exception as e:
            logger.error("workflow_failed", task_id=task_id, error=str(e))
            self._update_task(task_id, {"status": "failed", "error": str(e)})
            
            result["error"] = str(e)
            result["success"] = False
            
            # Notify failure
            self.slack.send_notification("escalation", {
                "ticket_id": ticket_id,
                "error": str(e)
            })
        
        return result
    
    def run_from_jira(self, ticket_key: str, auto_approve: bool = True) -> Dict[str, Any]:
        """Run workflow for a Jira ticket by key.
        
        Args:
            ticket_key: Jira ticket key (e.g., PROJ-123)
            auto_approve: Auto-approve the plan for testing
            
        Returns:
            Workflow result
        """
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
        """Run workflow from a text description.
        
        Args:
            description: Feature description
            title: Optional title
            auto_approve: Auto-approve for testing
            
        Returns:
            Workflow result
        """
        return self.run_full_workflow({
            "id": f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "summary": title or description[:100],
            "description": description,
            "labels": [],
            "priority": "Medium"
        }, auto_approve=auto_approve)
    
    def run_sentry_monitoring(self) -> Dict[str, Any]:
        """Run Sentry error monitoring.
        
        This simulates the EventBridge-triggered Sentry agent.
        
        Returns:
            Monitoring result
        """
        logger.info("sentry_monitoring_triggered")
        return self.sentry.run()
    
    def handle_slack_command(self, command: str, args: list, user_id: str = "local") -> str:
        """Handle a Slack slash command.
        
        Args:
            command: Command name
            args: Command arguments
            user_id: User ID
            
        Returns:
            Response message
        """
        return self.slack.handle_command(command, args, user_id)
    
    def _update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update task in local store."""
        updates["last_update"] = datetime.utcnow().isoformat()
        self.task_store.update_item(f"TASK#{task_id}", "METADATA", updates)
