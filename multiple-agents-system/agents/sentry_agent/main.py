"""
Sentry Monitoring Agent Implementation
=======================================
Monitors Sentry for recurring errors and creates Jira tickets.
"""

import json
import os
from datetime import datetime, timedelta
import boto3
import structlog
from langchain_aws import ChatBedrock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import settings


logger = structlog.get_logger(__name__)


class SentryAgent:
    """Agent for monitoring Sentry errors."""
    
    def __init__(self, agentcore_gateway):
        """Initialize the Sentry agent."""
        self.llm = ChatBedrock(
            model_id=settings.models.sentry_model,
            region_name=settings.aws.region
        )
        self.sentry_mcp = agentcore_gateway.get_tool("sentry-mcp")
        self.jira_mcp = agentcore_gateway.get_tool("jira-mcp")
        self.slack = agentcore_gateway.get_tool("slack")
        
        self.dynamodb = boto3.resource("dynamodb")
        self.error_tracking_table = self.dynamodb.Table(settings.dynamodb.error_tracking_table)
        
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "sentry"
        )
        
        with open(os.path.join(prompts_dir, "system.md")) as f:
            self.system_prompt = f.read()
    
    async def monitor_errors(self) -> dict:
        """Main monitoring loop (called by EventBridge hourly)."""
        stats = {"processed": 0, "tickets_created": 0, "deduplicated": 0}
        
        issues = await self.sentry_mcp.list_issues(
            project="all",
            query="is:unresolved",
            statsPeriod="24h"
        )
        
        for issue in issues:
            stats["processed"] += 1
            
            event_count = issue.get("count", 0)
            level = issue.get("level", "error")
            threshold = settings.sentry.thresholds.get(level, 10)
            
            if event_count >= threshold:
                existing_ticket = await self._check_existing_ticket(issue["id"])
                
                if existing_ticket:
                    stats["deduplicated"] += 1
                else:
                    await self._create_jira_ticket_from_error(issue)
                    stats["tickets_created"] += 1
        
        return stats
    
    async def _create_jira_ticket_from_error(self, sentry_issue: dict):
        """Create Jira ticket with AI label."""
        latest_event = await self.sentry_mcp.get_latest_event(
            issue_id=sentry_issue["id"]
        )
        
        stack_trace = self._extract_stack_trace(latest_event)
        
        description = f"""## Sentry Error Report

**Error:** {sentry_issue['title']}
**Type:** {sentry_issue.get('type', 'Unknown')}
**Level:** {sentry_issue.get('level', 'error')}

### Statistics (24h)
- **Event Count:** {sentry_issue.get('count', 0)}
- **Affected Users:** {sentry_issue.get('userCount', 'Unknown')}
- **First Seen:** {sentry_issue.get('firstSeen', 'Unknown')}
- **Last Seen:** {sentry_issue.get('lastSeen', 'Unknown')}

### Stack Trace
```
{stack_trace}
```

### Environment
- **Platform:** {latest_event.get('platform', 'Unknown')}
- **Release:** {latest_event.get('release', 'Unknown')}
- **Environment:** {latest_event.get('environment', 'Unknown')}

### Sentry Link
{sentry_issue.get('permalink', '')}

---
*This ticket was automatically created by the AI Sentry Agent*
*Error Fingerprint: {sentry_issue['id']}*
"""
        
        priority_map = {"fatal": "Critical", "error": "High", "warning": "Medium", "info": "Low"}
        priority = priority_map.get(sentry_issue.get('level', 'error'), 'Medium')
        
        ticket = await self.jira_mcp.create_issue(
            project=settings.jira.project_key,
            issue_type="Bug",
            summary=f"[AUTO] {sentry_issue['title'][:80]}",
            description=description,
            labels=[settings.jira.ai_label, settings.jira.auto_label, settings.jira.error_label],
            priority=priority
        )
        
        ttl_time = int((datetime.utcnow() + timedelta(days=90)).timestamp())
        self.error_tracking_table.put_item(
            Item={
                "error_fingerprint": sentry_issue["id"],
                "ticket_id": ticket["key"],
                "created_at": datetime.utcnow().isoformat(),
                "ttl": ttl_time
            }
        )
        
        await self.slack.send_message(
            channel=settings.slack.channel_errors,
            text=f"🐛 Auto-created ticket for recurring error:\n*{ticket['key']}:* {sentry_issue['title']}"
        )
        
        logger.info(
            "created_ticket_from_sentry",
            ticket=ticket["key"],
            error_id=sentry_issue["id"],
            event_count=sentry_issue.get("count", 0)
        )
    
    async def _check_existing_ticket(self, error_fingerprint: str) -> str | None:
        """Check if we already created a ticket for this error."""
        try:
            response = self.error_tracking_table.get_item(
                Key={"error_fingerprint": error_fingerprint}
            )
            
            if 'Item' in response:
                return response['Item']['ticket_id']
        except Exception as e:
            logger.error("dynamodb_error", error=str(e))
        
        return None
    
    def _extract_stack_trace(self, event: dict) -> str:
        """Extract stack trace from Sentry event."""
        try:
            exception = event.get('exception', {})
            values = exception.get('values', [])
            
            if values:
                frames = values[0].get('stacktrace', {}).get('frames', [])
                trace_lines = []
                
                for frame in frames[-10:]:
                    filename = frame.get('filename', 'unknown')
                    lineno = frame.get('lineno', '?')
                    function = frame.get('function', 'unknown')
                    trace_lines.append(f"  File \"{filename}\", line {lineno}, in {function}")
                
                return "\n".join(trace_lines)
        except Exception:
            pass
        
        return "Stack trace not available"


async def handler(event, context):
    """Lambda handler for Sentry agent."""
    from agents.shared.gateway import AgentCoreGateway
    
    gateway = AgentCoreGateway()
    agent = SentryAgent(gateway)
    
    result = await agent.monitor_errors()
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
