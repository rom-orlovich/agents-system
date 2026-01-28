"""TDD tests for GitHub webhook Slack button functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json


class TestGitHubSlackButtons:
    """Test GitHub task completion shows buttons in Slack notifications."""
    
    @pytest.mark.asyncio
    async def test_github_completion_shows_buttons_for_approval_required_command(self):
        """
        Business Rule: GitHub tasks requiring approval should show buttons in Slack.
        Behavior: When command requires approval, Block Kit blocks include actions block with buttons.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {
                "full_name": "owner/repo",
                "name": "repo",
                "owner": {"login": "owner"}
            },
            "pull_request": {
                "number": 42
            },
            "routing": {
                "source": "github"
            }
        }
        
        with patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.extract_task_summary') as mock_extract, \
             patch('api.webhooks.github.routes.build_task_completion_blocks') as mock_build, \
             patch('api.webhooks.github.routes.slack_client.post_message', new_callable=AsyncMock) as mock_slack:
            
            mock_extract.return_value = {"summary": "Fix implemented", "classification": "WORKFLOW"}
            mock_build.return_value = [
                {"type": "header", "text": {"type": "plain_text", "text": "Task Completed"}},
                {"type": "actions", "elements": [{"type": "button", "action_id": "approve_task"}]}
            ]
            
            await handle_github_task_completion(
                payload=payload,
                message="Fix implemented",
                success=True,
                cost_usd=0.0,
                task_id="task-123",
                command="fix",
                result="Fix summary"
            )
            
            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args.kwargs
            assert call_kwargs["requires_approval"] is True
            assert call_kwargs["source"] == "github"
            assert call_kwargs["routing"]["repo"] == "owner/repo"
            assert call_kwargs["routing"]["pr_number"] == 42
            
            mock_slack.assert_called_once()
            call_args = mock_slack.call_args
            assert "blocks" in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_github_completion_no_buttons_for_no_approval_command(self):
        """
        Business Rule: GitHub tasks not requiring approval should not show buttons.
        Behavior: When command doesn't require approval, build_task_completion_blocks is not called.
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {
                "full_name": "owner/repo",
                "owner": {"login": "owner"}
            },
            "issue": {
                "number": 10
            }
        }
        
        with patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.extract_task_summary') as mock_extract, \
             patch('api.webhooks.github.routes.build_task_completion_blocks') as mock_build, \
             patch('api.webhooks.github.routes.slack_client.post_message', new_callable=AsyncMock) as mock_slack:
            
            await handle_github_task_completion(
                payload=payload,
                message="Analysis complete",
                success=True,
                cost_usd=0.0,
                task_id="task-456",
                command="analyze",
                result="Analysis result"
            )
            
            mock_build.assert_not_called()
            mock_slack.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_github_completion_extracts_routing_metadata(self):
        """
        Business Rule: GitHub routing metadata must be extracted and included in button values.
        Behavior: Button values contain repo, pr_number, and source="github".
        """
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {
                "full_name": "test-org/test-repo",
                "name": "test-repo",
                "owner": {"login": "test-org"}
            },
            "pull_request": {
                "number": 99
            }
        }
        
        with patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.extract_task_summary') as mock_extract, \
             patch('api.webhooks.github.routes.build_task_completion_blocks') as mock_build, \
             patch('api.webhooks.github.routes.slack_client.post_message', new_callable=AsyncMock):
            
            mock_extract.return_value = {"summary": "Fix", "classification": "WORKFLOW"}
            mock_build.return_value = []
            
            await handle_github_task_completion(
                payload=payload,
                message="Fix implemented",
                success=True,
                cost_usd=0.0,
                task_id="task-789",
                command="fix",
                result="Fix"
            )
            
            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args.kwargs
            routing = call_kwargs["routing"]
            assert routing["repo"] == "test-org/test-repo"
            assert routing["pr_number"] == 99
            assert call_kwargs["source"] == "github"
    
    @pytest.mark.asyncio
    async def test_github_completion_posts_to_slack_channel(self):
        """
        Business Rule: GitHub completion must post Block Kit message to Slack channel.
        Behavior: slack_client.post_message() is called with correct channel and blocks.
        """
        import os
        from api.webhooks.github.routes import handle_github_task_completion
        
        payload = {
            "repository": {
                "full_name": "owner/repo",
                "owner": {"login": "owner"}
            },
            "pull_request": {
                "number": 5
            }
        }
        
        with patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock), \
             patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.github.routes.extract_task_summary') as mock_extract, \
             patch('api.webhooks.github.routes.build_task_completion_blocks') as mock_build, \
             patch('api.webhooks.github.routes.slack_client.post_message', new_callable=AsyncMock) as mock_slack, \
             patch.dict(os.environ, {"SLACK_CHANNEL_AGENTS": "#test-channel"}):
            
            mock_extract.return_value = {"summary": "Fix", "classification": "WORKFLOW"}
            mock_build.return_value = [{"type": "header", "text": {"type": "plain_text", "text": "Task"}}]
            
            await handle_github_task_completion(
                payload=payload,
                message="Fix implemented",
                success=True,
                cost_usd=0.0,
                task_id="task-111",
                command="fix",
                result="Fix"
            )
            
            mock_slack.assert_called_once()
            call_kwargs = mock_slack.call_args.kwargs
            assert call_kwargs["channel"] == "#test-channel"
            assert "blocks" in call_kwargs
    
    @pytest.mark.asyncio
    async def test_approve_button_posts_to_github_pr(self):
        """
        Business Rule: Approve button click must post @agent approve to GitHub PR.
        Behavior: create_task_from_button_action() creates GitHub task that posts comment.
        """
        from api.webhooks.slack.utils import create_task_from_button_action
        from sqlalchemy.ext.asyncio import AsyncSession
        
        routing = {
            "repo": "owner/repo",
            "pr_number": 42
        }
        
        mock_db = MagicMock(spec=AsyncSession)
        
        with patch('api.webhooks.github.utils.create_github_task', new_callable=AsyncMock) as mock_create, \
             patch('api.webhooks.github.utils.github_client') as mock_github:
            
            mock_create.return_value = "task-new-123"
            
            task_id = await create_task_from_button_action(
                action="approve",
                routing=routing,
                source="github",
                original_task_id="task-original",
                command="plan",
                db=mock_db,
                user_name="testuser"
            )
            
            assert task_id == "task-new-123"
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args
            payload = call_kwargs[0][1]
            assert payload["comment"]["body"] == "@agent approve\n\n_Triggered via Slack by @testuser_"
            assert payload["repository"]["full_name"] == "owner/repo"
            assert payload["issue"]["number"] == 42
    
    @pytest.mark.asyncio
    async def test_reject_button_posts_to_github_pr(self):
        """
        Business Rule: Reject button click must post @agent reject to GitHub PR.
        Behavior: create_task_from_button_action() creates GitHub task with reject command.
        """
        from api.webhooks.slack.utils import create_task_from_button_action
        from sqlalchemy.ext.asyncio import AsyncSession
        
        routing = {
            "repo": "owner/repo",
            "pr_number": 42
        }
        
        mock_db = MagicMock(spec=AsyncSession)
        
        with patch('api.webhooks.github.utils.create_github_task', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "task-new-456"
            
            task_id = await create_task_from_button_action(
                action="reject",
                routing=routing,
                source="github",
                original_task_id="task-original",
                command="plan",
                db=mock_db,
                user_name="testuser"
            )
            
            assert task_id == "task-new-456"
            call_kwargs = mock_create.call_args
            payload = call_kwargs[0][1]
            assert "@agent reject" in payload["comment"]["body"]
    
    @pytest.mark.asyncio
    async def test_review_button_posts_to_github_pr(self):
        """
        Business Rule: Review button click must post @agent review to GitHub PR.
        Behavior: create_task_from_button_action() creates GitHub task with review command.
        """
        from api.webhooks.slack.utils import create_task_from_button_action
        from sqlalchemy.ext.asyncio import AsyncSession
        
        routing = {
            "repo": "owner/repo",
            "pr_number": 42
        }
        
        mock_db = MagicMock(spec=AsyncSession)
        
        with patch('api.webhooks.github.utils.create_github_task', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "task-new-789"
            
            task_id = await create_task_from_button_action(
                action="review",
                routing=routing,
                source="github",
                original_task_id="task-original",
                command="plan",
                db=mock_db,
                user_name="testuser"
            )
            
            assert task_id == "task-new-789"
            call_kwargs = mock_create.call_args
            payload = call_kwargs[0][1]
            assert "@agent review" in payload["comment"]["body"]
    
    @pytest.mark.asyncio
    async def test_button_values_contain_github_routing(self):
        """
        Business Rule: Button values must include GitHub routing metadata.
        Behavior: Button values contain repo, pr_number, and source="github".
        """
        from api.webhooks.slack.utils import build_task_completion_blocks
        
        routing = {
            "repo": "test-org/test-repo",
            "pr_number": 123
        }
        
        blocks = build_task_completion_blocks(
            summary={"summary": "Test", "classification": "WORKFLOW"},
            routing=routing,
            requires_approval=True,
            task_id="task-test",
            cost_usd=0.0,
            command="plan",
            source="github"
        )
        
        actions_blocks = [b for b in blocks if b.get("type") == "actions"]
        assert len(actions_blocks) > 0
        
        buttons = actions_blocks[0]["elements"]
        for button in buttons:
            value_str = button.get("value", "{}")
            value = json.loads(value_str)
            assert value["source"] == "github"
            assert value["routing"]["repo"] == "test-org/test-repo"
            assert value["routing"]["pr_number"] == 123
