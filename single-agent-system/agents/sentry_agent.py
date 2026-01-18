"""
Sentry Monitoring Agent Implementation
=======================================
Monitors Sentry for recurring errors and creates Jira tickets.
Mirrors the distributed system's sentry_agent/main.py
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import structlog
from langchain_aws import ChatBedrock

from config import settings

logger = structlog.get_logger(__name__)


class SentryAgent:
    """Agent for monitoring Sentry errors."""
    
    def __init__(self, mcp_gateway):
        """Initialize the Sentry agent."""
        self.llm = ChatBedrock(
            model_id=settings.bedrock.verification_model,
            region_name=settings.aws.region,
            model_kwargs={
                "max_tokens": settings.bedrock.max_tokens,
                "temperature": settings.bedrock.temperature
            }
        )
        self.sentry_mcp = mcp_gateway.get_tool("sentry-mcp")
        self.jira_mcp = mcp_gateway.get_tool("jira-mcp")
        self.slack = mcp_gateway.get_tool("slack")
        self.task_store = mcp_gateway.get_task_store()
        
        self._load_prompts()
        logger.info("sentry_agent_initialized", model=settings.bedrock.verification_model)
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "sentry"
        
        system_prompt_path = prompts_dir / "system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text()
        else:
            self.system_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        return """You are the Sentry Monitoring Agent for an enterprise software organization.
Your mission is to monitor Sentry for recurring errors and create Jira tickets."""
    
    def monitor_errors(self) -> Dict[str, Any]:
        """Main monitoring loop."""
        stats = {"processed": 0, "tickets_created": 0, "deduplicated": 0}
        
        logger.info("sentry_monitoring_started")
        
        # Get unresolved issues from Sentry
        issues = self.sentry_mcp.get_issues(query="is:unresolved", limit=50)
        
        for issue in issues:
            stats["processed"] += 1
            
            # Check if exceeds threshold
            if self.sentry_mcp.should_escalate(issue):
                # Check for existing ticket
                existing = self._check_existing_ticket(issue["id"])
                
                if existing:
                    stats["deduplicated"] += 1
                    logger.debug("error_deduplicated", issue_id=issue["id"])
                else:
                    # Create Jira ticket
                    self._create_jira_ticket_from_error(issue)
                    stats["tickets_created"] += 1
        
        logger.info("sentry_monitoring_complete", **stats)
        return stats
    
    def _create_jira_ticket_from_error(self, sentry_issue: Dict[str, Any]):
        """Create Jira ticket with AI label."""
        # Get event details
        events = self.sentry_mcp.get_issue_events(sentry_issue["id"], limit=1)
        latest_event = events[0] if events else {}
        
        stack_trace = self._format_stack_trace(latest_event)
        
        description = f"""## Sentry Error Report

**Error:** {sentry_issue['title']}
**Level:** {sentry_issue.get('level', 'error')}

### Statistics (24h)
- **Event Count:** {sentry_issue.get('count', 0)}
- **First Seen:** {sentry_issue.get('first_seen', 'Unknown')}
- **Last Seen:** {sentry_issue.get('last_seen', 'Unknown')}

### Stack Trace
```
{stack_trace}
```

### Sentry Link
{sentry_issue.get('url', '')}

---
*This ticket was automatically created by the AI Sentry Agent*
*Error ID: {sentry_issue['id']}*
"""
        
        priority_map = {"fatal": "Critical", "error": "High", "warning": "Medium", "info": "Low"}
        priority = priority_map.get(sentry_issue.get("level", "error"), "Medium")
        
        # Create ticket
        ticket = self.jira_mcp.create_issue(
            summary=f"[AUTO] {sentry_issue['title'][:80]}",
            description=description,
            issue_type="Bug",
            labels=[settings.jira.ai_label, settings.jira.auto_label, settings.jira.error_label],
            priority=priority
        )
        
        if ticket:
            # Store mapping to prevent duplicates
            self.task_store.put_item({
                "pk": f"ERROR#{sentry_issue['id']}",
                "sk": "TICKET",
                "ticket_id": ticket["key"],
                "created_at": datetime.utcnow().isoformat()
            })
            
            # Notify Slack
            self.slack.send_message(
                text=f"🐛 Auto-created ticket for recurring error:\n*{ticket['key']}:* {sentry_issue['title'][:50]}",
                channel=settings.slack.channel_errors
            )
            
            logger.info("sentry_ticket_created", ticket=ticket["key"], error_id=sentry_issue["id"])
    
    def _check_existing_ticket(self, error_id: str) -> Optional[str]:
        """Check if we already created a ticket for this error."""
        item = self.task_store.get_item(f"ERROR#{error_id}", "TICKET")
        if item:
            return item.get("ticket_id")
        return None
    
    def _format_stack_trace(self, event: Dict[str, Any]) -> str:
        """Format stack trace from event."""
        entries = event.get("entries", {})
        
        if "exception" in entries:
            exc = entries["exception"]
            stacktrace = exc.get("stacktrace", [])
            
            lines = []
            for frame in stacktrace[-10:]:
                filename = frame.get("filename", "unknown")
                lineno = frame.get("lineno", "?")
                function = frame.get("function", "unknown")
                lines.append(f'  File "{filename}", line {lineno}, in {function}')
            
            return "\n".join(lines) if lines else "Stack trace not available"
        
        return "Stack trace not available"
    
    def run(self, request: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run Sentry monitoring.
        
        Args:
            request: Optional request parameters
            
        Returns:
            MonitoringResult dict
        """
        return self.monitor_errors()
