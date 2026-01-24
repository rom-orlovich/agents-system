"""Workflow orchestration for intelligent code analysis and cross-service coordination.

This module provides orchestration logic for complex workflows like:
- Jira ticket assignment → code analysis → PR creation → notifications
- GitHub issue → analysis → Jira ticket creation
- Sentry error → analysis → fix implementation
"""

import os
import json
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from core.jira_client import jira_client
from core.slack_client import slack_client
from core.sentry_client import sentry_client
from core.github_client import github_client

logger = structlog.get_logger()


class WorkflowOrchestrator:
    """Orchestrates complex workflows across multiple services."""

    def __init__(self):
        """Initialize orchestrator with service clients."""
        self.jira = jira_client
        self.slack = slack_client
        self.sentry = sentry_client
        self.github = github_client
        self.notification_channel = os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity")

    async def notify_workflow_start(
        self,
        workflow_name: str,
        details: Dict[str, Any],
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """
        Send notification when workflow starts.

        Args:
            workflow_name: Name of the workflow
            details: Workflow details
            thread_ts: Optional thread to reply in

        Returns:
            Message timestamp for threading
        """
        try:
            response = await self.slack.send_workflow_notification(
                channel=self.notification_channel,
                workflow_name=workflow_name,
                status="started",
                details=details,
                thread_ts=thread_ts
            )
            return response.get("ts")
        except Exception as e:
            logger.error("workflow_notification_failed", workflow=workflow_name, error=str(e))
            return None

    async def notify_workflow_progress(
        self,
        workflow_name: str,
        status: str,
        details: Dict[str, Any],
        thread_ts: Optional[str] = None
    ) -> None:
        """Send progress notification for workflow."""
        try:
            await self.slack.send_workflow_notification(
                channel=self.notification_channel,
                workflow_name=workflow_name,
                status=status,
                details=details,
                thread_ts=thread_ts
            )
        except Exception as e:
            logger.error("workflow_progress_notification_failed", workflow=workflow_name, error=str(e))

    async def notify_workflow_complete(
        self,
        workflow_name: str,
        details: Dict[str, Any],
        thread_ts: Optional[str] = None
    ) -> None:
        """Send notification when workflow completes."""
        try:
            await self.slack.send_workflow_notification(
                channel=self.notification_channel,
                workflow_name=workflow_name,
                status="completed",
                details=details,
                thread_ts=thread_ts
            )
        except Exception as e:
            logger.error("workflow_complete_notification_failed", workflow=workflow_name, error=str(e))

    async def notify_workflow_failure(
        self,
        workflow_name: str,
        error: str,
        thread_ts: Optional[str] = None
    ) -> None:
        """Send notification when workflow fails."""
        try:
            await self.slack.send_workflow_notification(
                channel=self.notification_channel,
                workflow_name=workflow_name,
                status="failed",
                details={"Error": error},
                thread_ts=thread_ts
            )
        except Exception as e:
            logger.error("workflow_failure_notification_failed", workflow=workflow_name, error=str(e))

    async def jira_ticket_analysis_workflow(
        self,
        payload: Dict[str, Any],
        analysis_result: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Execute workflow for Jira ticket assignment → analysis → comment.

        Args:
            payload: Jira webhook payload
            analysis_result: Analysis text from planning agent
            task_id: Task ID for tracking

        Returns:
            Workflow result dict
        """
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        workflow_name = f"Jira Analysis: {issue_key}"

        logger.info("jira_analysis_workflow_start", issue_key=issue_key, task_id=task_id)

        # Send start notification
        thread_ts = await self.notify_workflow_start(
            workflow_name,
            {
                "Issue": issue_key,
                "Task ID": task_id,
                "Summary": issue.get("fields", {}).get("summary", "N/A")
            }
        )

        result = {
            "workflow": "jira_analysis",
            "issue_key": issue_key,
            "task_id": task_id,
            "steps": []
        }

        try:
            # Step 1: Post analysis to Jira
            await self.notify_workflow_progress(
                workflow_name,
                "in_progress",
                {"Step": "Posting analysis to Jira"},
                thread_ts
            )

            await self.jira.post_comment(issue_key, analysis_result)

            result["steps"].append({
                "name": "post_jira_comment",
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Workflow complete
            await self.notify_workflow_complete(
                workflow_name,
                {
                    "Issue": issue_key,
                    "Status": "Analysis posted to Jira",
                    "Task ID": task_id
                },
                thread_ts
            )

            result["status"] = "completed"
            logger.info("jira_analysis_workflow_complete", issue_key=issue_key, task_id=task_id)

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("jira_analysis_workflow_failed", issue_key=issue_key, error=error_msg)

            result["status"] = "failed"
            result["error"] = error_msg

            await self.notify_workflow_failure(workflow_name, error_msg, thread_ts)

            return result

    async def jira_ticket_with_pr_workflow(
        self,
        payload: Dict[str, Any],
        analysis_result: str,
        pr_url: Optional[str],
        task_id: str
    ) -> Dict[str, Any]:
        """
        Execute workflow for Jira ticket → analysis → PR creation → link back.

        Args:
            payload: Jira webhook payload
            analysis_result: Analysis text
            pr_url: GitHub PR URL (if created)
            task_id: Task ID

        Returns:
            Workflow result dict
        """
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        workflow_name = f"Jira Fix: {issue_key}"

        logger.info("jira_pr_workflow_start", issue_key=issue_key, pr_url=pr_url, task_id=task_id)

        # Send start notification
        thread_ts = await self.notify_workflow_start(
            workflow_name,
            {
                "Issue": issue_key,
                "Task ID": task_id,
                "Summary": issue.get("fields", {}).get("summary", "N/A")
            }
        )

        result = {
            "workflow": "jira_with_pr",
            "issue_key": issue_key,
            "pr_url": pr_url,
            "task_id": task_id,
            "steps": []
        }

        try:
            # Step 1: Post analysis to Jira
            await self.notify_workflow_progress(
                workflow_name,
                "in_progress",
                {"Step": "Posting analysis to Jira"},
                thread_ts
            )

            await self.jira.post_comment(issue_key, analysis_result)

            result["steps"].append({
                "name": "post_analysis_comment",
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Step 2: If PR created, link it to Jira
            if pr_url:
                await self.notify_workflow_progress(
                    workflow_name,
                    "in_progress",
                    {"Step": f"Linking PR to Jira", "PR": pr_url},
                    thread_ts
                )

                # Add remote link
                await self.jira.add_remote_link(
                    issue_key,
                    pr_url,
                    f"GitHub PR for {issue_key}",
                    "fixes"
                )

                # Post comment with PR link
                pr_comment = f"🔧 Created draft PR: {pr_url}\n\nPlease review the proposed changes."
                await self.jira.post_comment(issue_key, pr_comment)

                result["steps"].append({
                    "name": "link_pr_to_jira",
                    "status": "completed",
                    "pr_url": pr_url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # Workflow complete
            completion_details = {
                "Issue": issue_key,
                "Task ID": task_id
            }

            if pr_url:
                completion_details["PR"] = pr_url
                completion_details["Status"] = "Analysis and PR posted to Jira"
            else:
                completion_details["Status"] = "Analysis posted to Jira (no PR created)"

            await self.notify_workflow_complete(workflow_name, completion_details, thread_ts)

            result["status"] = "completed"
            logger.info("jira_pr_workflow_complete", issue_key=issue_key, pr_url=pr_url, task_id=task_id)

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("jira_pr_workflow_failed", issue_key=issue_key, error=error_msg)

            result["status"] = "failed"
            result["error"] = error_msg

            await self.notify_workflow_failure(workflow_name, error_msg, thread_ts)

            return result

    async def github_issue_analysis_workflow(
        self,
        payload: Dict[str, Any],
        analysis_result: str,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Execute workflow for GitHub issue → analysis → comment.

        Args:
            payload: GitHub webhook payload
            analysis_result: Analysis text
            task_id: Task ID

        Returns:
            Workflow result dict
        """
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        owner = repo.get("owner", {}).get("login")
        repo_name = repo.get("name")
        issue_number = issue.get("number")

        workflow_name = f"GitHub Analysis: {owner}/{repo_name}#{issue_number}"

        logger.info("github_analysis_workflow_start", repo=f"{owner}/{repo_name}", issue=issue_number, task_id=task_id)

        # Send start notification
        thread_ts = await self.notify_workflow_start(
            workflow_name,
            {
                "Repository": f"{owner}/{repo_name}",
                "Issue": f"#{issue_number}",
                "Task ID": task_id
            }
        )

        result = {
            "workflow": "github_analysis",
            "repo": f"{owner}/{repo_name}",
            "issue_number": issue_number,
            "task_id": task_id,
            "steps": []
        }

        try:
            # Post analysis to GitHub
            await self.notify_workflow_progress(
                workflow_name,
                "in_progress",
                {"Step": "Posting analysis to GitHub"},
                thread_ts
            )

            await self.github.post_issue_comment(owner, repo_name, issue_number, analysis_result)

            result["steps"].append({
                "name": "post_github_comment",
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Workflow complete
            await self.notify_workflow_complete(
                workflow_name,
                {
                    "Repository": f"{owner}/{repo_name}",
                    "Issue": f"#{issue_number}",
                    "Status": "Analysis posted to GitHub"
                },
                thread_ts
            )

            result["status"] = "completed"
            logger.info("github_analysis_workflow_complete", repo=f"{owner}/{repo_name}", issue=issue_number)

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("github_analysis_workflow_failed", repo=f"{owner}/{repo_name}", issue=issue_number, error=error_msg)

            result["status"] = "failed"
            result["error"] = error_msg

            await self.notify_workflow_failure(workflow_name, error_msg, thread_ts)

            return result


# Global orchestrator instance
workflow_orchestrator = WorkflowOrchestrator()
