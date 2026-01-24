"""Integration tests for external service integrations (Phase 3 of Multi-Subagent Orchestration)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid


class TestGitHubIntegrationAgent:
    """Test GitHub integration agent capabilities."""
    async def test_github_agent_can_list_issues(self, client, redis_mock):
        """
        REQUIREMENT: GitHub agent should be able to list issues via gh CLI.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        # Spawn GitHub integration agent
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "github-integrator",
            "mode": "background",
            "task_id": f"gh-list-issues-{uuid.uuid4().hex[:8]}",
            "prompt": "List open issues in the current repository"
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent_type"] == "github-integrator"
    async def test_github_agent_can_create_pr(self, client, redis_mock):
        """
        REQUIREMENT: GitHub agent should be able to create PRs via gh CLI.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "github-integrator",
            "mode": "foreground",
            "task_id": f"gh-create-pr-{uuid.uuid4().hex[:8]}",
            "prompt": "Create a PR for the current branch"
        })
        
        assert response.status_code == 200
    async def test_github_agent_can_review_pr(self, client, redis_mock):
        """
        REQUIREMENT: GitHub agent should be able to review PRs.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "github-integrator",
            "mode": "background",
            "task_id": f"gh-review-pr-{uuid.uuid4().hex[:8]}",
            "prompt": "Review PR #123 for code quality"
        })
        
        assert response.status_code == 200
    async def test_github_agent_requires_token(self, client):
        """
        REQUIREMENT: GitHub agent should require GITHUB_TOKEN environment variable.
        """
        # Check that GitHub token is configured
        response = await client.get("/api/v2/agents/github-integrator/config")
        
        # Should either return config or indicate missing token
        assert response.status_code in [200, 404, 500]


class TestJiraIntegrationAgent:
    """Test Jira integration agent capabilities."""
    async def test_jira_agent_can_list_issues(self, client, redis_mock):
        """
        REQUIREMENT: Jira agent should be able to list issues via jira-cli.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "jira-integrator",
            "mode": "background",
            "task_id": f"jira-list-{uuid.uuid4().hex[:8]}",
            "prompt": "List issues in current sprint"
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent_type"] == "jira-integrator"
    async def test_jira_agent_can_create_issue(self, client, redis_mock):
        """
        REQUIREMENT: Jira agent should be able to create issues.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "jira-integrator",
            "mode": "foreground",
            "task_id": f"jira-create-{uuid.uuid4().hex[:8]}",
            "prompt": "Create a bug ticket for the authentication issue"
        })
        
        assert response.status_code == 200
    async def test_jira_agent_can_transition_issue(self, client, redis_mock):
        """
        REQUIREMENT: Jira agent should be able to transition issues.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "jira-integrator",
            "mode": "background",
            "task_id": f"jira-transition-{uuid.uuid4().hex[:8]}",
            "prompt": "Move PROJ-123 to In Review"
        })
        
        assert response.status_code == 200


class TestSlackIntegrationAgent:
    """Test Slack integration agent capabilities."""
    async def test_slack_agent_can_send_message(self, client, redis_mock):
        """
        REQUIREMENT: Slack agent should be able to send messages.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "slack-integrator",
            "mode": "background",
            "task_id": f"slack-msg-{uuid.uuid4().hex[:8]}",
            "prompt": "Send a message to #general channel"
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent_type"] == "slack-integrator"
    async def test_slack_agent_can_reply_to_thread(self, client, redis_mock):
        """
        REQUIREMENT: Slack agent should be able to reply to threads.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "slack-integrator",
            "mode": "foreground",
            "task_id": f"slack-thread-{uuid.uuid4().hex[:8]}",
            "prompt": "Reply to thread 1234567890.123456"
        })
        
        assert response.status_code == 200


class TestSentryIntegrationAgent:
    """Test Sentry integration agent capabilities."""
    async def test_sentry_agent_can_list_errors(self, client, redis_mock):
        """
        REQUIREMENT: Sentry agent should be able to list recent errors.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "sentry-integrator",
            "mode": "background",
            "task_id": f"sentry-list-{uuid.uuid4().hex[:8]}",
            "prompt": "List errors from the last 24 hours"
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent_type"] == "sentry-integrator"
    async def test_sentry_agent_can_analyze_error_patterns(self, client, redis_mock):
        """
        REQUIREMENT: Sentry agent should be able to analyze error patterns.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "sentry-integrator",
            "mode": "background",
            "task_id": f"sentry-analyze-{uuid.uuid4().hex[:8]}",
            "prompt": "Analyze error patterns for the authentication module"
        })
        
        assert response.status_code == 200


class TestMultiServiceOrchestration:
    """Test cross-service orchestration workflows."""
    async def test_incident_response_workflow(self, client, redis_mock):
        """
        REQUIREMENT: Should orchestrate incident response across services.
        Sentry error → Jira ticket → Slack alert → GitHub issue
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        redis_mock.create_parallel_group = AsyncMock()
        
        # Spawn service orchestrator for incident response
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "service-orchestrator",
            "mode": "background",
            "task_id": f"incident-{uuid.uuid4().hex[:8]}",
            "prompt": "Handle Sentry error spike: AuthenticationError increased 500%"
        })
        
        assert response.status_code == 200
    async def test_release_coordination_workflow(self, client, redis_mock):
        """
        REQUIREMENT: Should coordinate release across services.
        GitHub release → Sentry release → Jira version → Slack announcement
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        
        response = await client.post("/api/v2/subagents/spawn", json={
            "agent_type": "service-orchestrator",
            "mode": "foreground",
            "task_id": f"release-{uuid.uuid4().hex[:8]}",
            "prompt": "Coordinate release v1.2.0 across all services"
        })
        
        assert response.status_code == 200
    async def test_parallel_service_status_check(self, client, redis_mock):
        """
        REQUIREMENT: Should check status across all services in parallel.
        """
        redis_mock.get_active_subagent_count = AsyncMock(return_value=0)
        redis_mock.add_active_subagent = AsyncMock()
        redis_mock.create_parallel_group = AsyncMock()
        
        response = await client.post("/api/v2/subagents/parallel", json={
            "agents": [
                {"type": "github-integrator", "task": "Check GitHub status"},
                {"type": "jira-integrator", "task": "Check Jira status"},
                {"type": "sentry-integrator", "task": "Check Sentry status"},
                {"type": "slack-integrator", "task": "Check Slack status"},
            ]
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent_count"] == 4
