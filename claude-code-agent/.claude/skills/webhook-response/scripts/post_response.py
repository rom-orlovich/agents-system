#!/usr/bin/env python3
"""
Post webhook analysis responses back to the source.

This script handles posting analysis results back to the webhook source
(GitHub, Jira, Slack, Sentry) after the brain agent completes analysis.
"""
import sys
import json
import asyncio
import structlog
from pathlib import Path

# Add project root to path dynamically
# This works whether running from Docker, local, or cloud
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent.parent.parent.parent  # Go up 4 levels from scripts/
sys.path.insert(0, str(project_root))

from core.workflow_orchestrator import workflow_orchestrator
from core.slack_client import slack_client
from core.sentry_client import sentry_client

logger = structlog.get_logger()


async def post_webhook_response(
    task,
    analysis_result: str
) -> bool:
    """
    Post analysis response back to webhook source.
    
    Args:
        task: Task object with source_metadata
        analysis_result: Analysis text to post
        
    Returns:
        True if posted successfully, False otherwise
    """
    try:
        # Extract metadata
        source_metadata = json.loads(task.source_metadata or "{}")
        webhook_source = source_metadata.get("webhook_source")
        payload = source_metadata.get("payload", {})
        task_id = task.task_id
        
        if not webhook_source:
            logger.warning("webhook_response_no_source", task_id=task_id)
            return False
        
        # Post based on source
        if webhook_source == "github":
            await workflow_orchestrator.github_issue_analysis_workflow(
                payload, analysis_result, task_id
            )
            logger.info("webhook_response_posted", source="github", task_id=task_id)
            return True
            
        elif webhook_source == "jira":
            await workflow_orchestrator.jira_ticket_analysis_workflow(
                payload, analysis_result, task_id
            )
            logger.info("webhook_response_posted", source="jira", task_id=task_id)
            return True
            
        elif webhook_source == "slack":
            # Extract Slack-specific data
            event = payload.get("event", {})
            channel = event.get("channel")
            thread_ts = event.get("ts")
            
            if not channel:
                logger.error("webhook_response_missing_channel", task_id=task_id)
                return False
            
            await slack_client.post_message(
                channel=channel,
                text=analysis_result,
                thread_ts=thread_ts
            )
            logger.info("webhook_response_posted", source="slack", task_id=task_id)
            return True
            
        elif webhook_source == "sentry":
            # Extract Sentry-specific data
            issue_data = payload.get("data", {}).get("issue", {})
            issue_id = issue_data.get("id")
            
            if not issue_id:
                logger.error("webhook_response_missing_issue_id", task_id=task_id)
                return False
            
            await sentry_client.add_comment(issue_id, analysis_result)
            logger.info("webhook_response_posted", source="sentry", task_id=task_id)
            return True
            
        else:
            logger.warning(
                "webhook_response_unknown_source",
                source=webhook_source,
                task_id=task_id
            )
            return False
            
    except Exception as e:
        logger.error(
            "webhook_response_failed",
            error=str(e),
            error_type=type(e).__name__,
            task_id=task.task_id if hasattr(task, 'task_id') else 'unknown'
        )
        return False


async def post_response_from_metadata(
    webhook_source: str,
    payload: dict,
    analysis_result: str,
    task_id: str
) -> bool:
    """
    Post response using raw metadata (alternative interface).
    
    Args:
        webhook_source: Source type (github, jira, slack, sentry)
        payload: Webhook payload
        analysis_result: Analysis text to post
        task_id: Task ID for logging
        
    Returns:
        True if posted successfully, False otherwise
    """
    # Create a minimal task-like object
    class TaskStub:
        def __init__(self, source_metadata, task_id):
            self.source_metadata = source_metadata
            self.task_id = task_id
    
    source_metadata = json.dumps({
        "webhook_source": webhook_source,
        "payload": payload
    })
    
    task_stub = TaskStub(source_metadata, task_id)
    return await post_webhook_response(task_stub, analysis_result)


if __name__ == "__main__":
    # CLI usage for testing
    if len(sys.argv) < 4:
        print("Usage: python post_response.py SOURCE TASK_ID ANALYSIS_FILE [PAYLOAD_FILE]")
        print("Example: python post_response.py github task-123 analysis.txt payload.json")
        sys.exit(1)
    
    source = sys.argv[1]
    task_id = sys.argv[2]
    analysis_file = sys.argv[3]
    payload_file = sys.argv[4] if len(sys.argv) > 4 else None
    
    # Read analysis
    with open(analysis_file, 'r') as f:
        analysis = f.read()
    
    # Read payload
    payload = {}
    if payload_file:
        with open(payload_file, 'r') as f:
            payload = json.load(f)
    
    # Post response
    success = asyncio.run(post_response_from_metadata(source, payload, analysis, task_id))
    
    if success:
        print(f"✅ Posted response to {source}")
        sys.exit(0)
    else:
        print(f"❌ Failed to post response to {source}")
        sys.exit(1)
