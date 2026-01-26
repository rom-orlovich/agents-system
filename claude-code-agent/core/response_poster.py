"""
Unified response posting interface.

Brain agent uses this to post responses back to webhook sources
without knowing the implementation details.
"""

import os
import json
import subprocess
from typing import Optional
import structlog

logger = structlog.get_logger()


class ResponsePoster:
    """
    Posts responses back to webhook sources.

    Usage:
        poster = ResponsePoster()
        await poster.post(source_metadata, result)
    """

    async def post(self, source_metadata: dict, result: str) -> bool:
        """
        Post response to the appropriate source.

        Args:
            source_metadata: Task's source_metadata containing routing info
            result: The response text to post

        Returns:
            True if successful, False otherwise
        """
        webhook_source = source_metadata.get("webhook_source", "")
        routing = source_metadata.get("routing", {})

        # Fallback: extract from payload if routing not present
        if not routing and "payload" in source_metadata:
            from core.routing_metadata import extract_routing_metadata
            routing = extract_routing_metadata(webhook_source, source_metadata["payload"])

        try:
            if webhook_source == "github":
                return await self._post_github(routing, result)
            elif webhook_source == "jira":
                return await self._post_jira(routing, result)
            elif webhook_source == "slack":
                return await self._post_slack(routing, result)
            else:
                logger.warning("unknown_webhook_source", source=webhook_source)
                return False
        except Exception as e:
            logger.error("response_post_failed", source=webhook_source, error=str(e))
            return False

    async def _post_github(self, routing: dict, result: str) -> bool:
        """Post response to GitHub PR or Issue."""
        owner = routing.get("owner")
        repo = routing.get("repo")

        if not owner or not repo:
            logger.error("github_routing_missing", routing=routing)
            return False

        # Import here to avoid circular imports
        try:
            from core.github_client import github_client

            # Prefer PR, fallback to issue
            if routing.get("pr_number"):
                await github_client.post_pr_comment(
                    owner, repo, routing["pr_number"], result
                )
                logger.info("github_response_posted", type="pr", number=routing["pr_number"])
                return True
            elif routing.get("issue_number"):
                await github_client.post_issue_comment(
                    owner, repo, routing["issue_number"], result
                )
                logger.info("github_response_posted", type="issue", number=routing["issue_number"])
                return True
            else:
                logger.error("github_no_pr_or_issue", routing=routing)
                return False

        except ImportError:
            # Fallback to script/curl if client not available
            return self._post_github_curl(owner, repo, routing, result)

    def _post_github_curl(self, owner: str, repo: str, routing: dict, result: str) -> bool:
        """Fallback: Post to GitHub using curl."""
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.error("github_token_missing")
            return False

        number = routing.get("pr_number") or routing.get("issue_number")
        if not number:
            return False

        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", url,
                    "-H", f"Authorization: Bearer {token}",
                    "-H", "Accept: application/vnd.github+json",
                    "-d", json.dumps({"body": result})
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            return proc.returncode == 0
        except Exception as e:
            logger.error("github_curl_failed", error=str(e))
            return False

    async def _post_jira(self, routing: dict, result: str) -> bool:
        """Post response to Jira ticket."""
        ticket_key = routing.get("ticket_key")
        if not ticket_key:
            logger.error("jira_ticket_key_missing", routing=routing)
            return False

        # Use the post_comment script
        script_path = ".claude/skills/jira-operations/scripts/post_comment.sh"

        try:
            proc = subprocess.run(
                [script_path, ticket_key, result],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.environ.get("AGENT_HOME", ".")
            )
            if proc.returncode == 0:
                logger.info("jira_response_posted", ticket=ticket_key)
                return True
            else:
                logger.error("jira_script_failed", stderr=proc.stderr)
                return False
        except FileNotFoundError:
            # Fallback to direct API call
            return await self._post_jira_api(ticket_key, result)
        except Exception as e:
            logger.error("jira_post_failed", error=str(e))
            return False

    async def _post_jira_api(self, ticket_key: str, result: str) -> bool:
        """Fallback: Post to Jira using direct API."""
        base_url = os.environ.get("JIRA_BASE_URL")
        email = os.environ.get("JIRA_USER_EMAIL")
        token = os.environ.get("JIRA_API_TOKEN")

        if not all([base_url, email, token]):
            logger.error("jira_credentials_missing")
            return False

        import base64
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()

        url = f"{base_url}/rest/api/3/issue/{ticket_key}/comment"

        # Simple text format (not ADF for simplicity)
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": result}]
                    }
                ]
            }
        }

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", url,
                    "-H", f"Authorization: Basic {auth}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(body)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            return proc.returncode == 0
        except Exception as e:
            logger.error("jira_api_failed", error=str(e))
            return False

    async def _post_slack(self, routing: dict, result: str) -> bool:
        """Post response to Slack thread."""
        channel_id = routing.get("channel_id")
        thread_ts = routing.get("thread_ts")

        if not channel_id:
            logger.error("slack_channel_missing", routing=routing)
            return False

        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            logger.error("slack_token_missing")
            return False

        payload = {
            "channel": channel_id,
            "text": result,
        }

        # Add thread_ts if available (reply in thread)
        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            proc = subprocess.run(
                [
                    "curl", "-s", "-X", "POST",
                    "https://slack.com/api/chat.postMessage",
                    "-H", f"Authorization: Bearer {token}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if proc.returncode == 0:
                response = json.loads(proc.stdout)
                if response.get("ok"):
                    logger.info("slack_response_posted", channel=channel_id)
                    return True
                else:
                    logger.error("slack_api_error", error=response.get("error"))
                    return False
            return False
        except Exception as e:
            logger.error("slack_post_failed", error=str(e))
            return False


# Singleton instance for easy access
response_poster = ResponsePoster()


async def post_response(source_metadata: dict, result: str) -> bool:
    """
    Convenience function to post response.

    Usage:
        from core.response_poster import post_response
        await post_response(task.source_metadata, "Analysis complete")
    """
    return await response_poster.post(source_metadata, result)
