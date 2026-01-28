"""TDD Integration tests verifying each part does its job in the full webhook process.

Tests verify the complete flow for each webhook:
1. Route receives webhook → validates → creates task with completion handler
2. Task worker picks up task → processes → calls completion handler
3. Completion handler posts comment → sends Slack notification
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy import select

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from workers.task_worker import TaskWorker
from core.websocket_hub import WebSocketHub
from core.database.models import TaskDB
from shared import TaskStatus


@pytest.mark.integration
class TestGitHubFullProcessVerification:
    """Verify each part does its job in GitHub webhook full process."""
    
    @pytest.mark.asyncio
    async def test_github_full_process_each_part_does_its_job(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Each part must do its job in the full GitHub webhook process.
        
        Process Steps:
        1. Route receives webhook → validates signature ✅
        2. Route validates payload → matches command ✅
        3. Route sends immediate response (reaction) ✅
        4. Route creates task → registers completion handler ✅
        5. Route queues task → returns HTTP response ✅
        6. Task worker picks up task → processes ✅
        7. Task worker calls completion handler ✅
        8. Completion handler formats message ✅
        9. Completion handler posts GitHub comment ✅
        10. Completion handler sends Slack notification ✅
        """
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
        
        payload = {
            "action": "created",
            "comment": {"id": 999, "body": "@agent review the pr"},
            "issue": {"number": 123, "pull_request": {}},
            "repository": {"owner": {"login": "test"}, "name": "repo"}
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": f"sha256={signature}"
        }
        
        step_tracker = {
            "route_received": False,
            "route_validated": False,
            "immediate_response_sent": False,
            "task_created_with_handler": False,
            "task_queued": False,
            "worker_processed": False,
            "handler_called": False,
            "comment_posted": False,
            "slack_notified": False
        }
        
        with patch('api.webhooks.github.utils.github_client.add_reaction', new_callable=AsyncMock) as mock_reaction, \
             patch('api.webhooks.github.utils.redis_client.push_task', new_callable=AsyncMock) as mock_queue, \
             patch('api.webhooks.github.routes.post_github_task_comment', new_callable=AsyncMock) as mock_post_comment, \
             patch('api.webhooks.github.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            mock_reaction.return_value = True
            mock_queue.return_value = None
            mock_post_comment.return_value = True
            
            # Step 1-5: Route receives, validates, creates task
            response = await client.post(
                "/webhooks/github",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201], "Route should accept valid webhook"
            step_tracker["route_received"] = True
            step_tracker["route_validated"] = True
            
            data = response.json()
            task_id = data.get("task_id")
            assert task_id is not None, "Task should be created"
            
            # Verify immediate response sent
            assert mock_reaction.called, "Immediate reaction should be sent"
            step_tracker["immediate_response_sent"] = True
            
            # Verify task queued
            assert mock_queue.called, "Task should be queued"
            step_tracker["task_queued"] = True
            
            # Step 4: Verify task created with completion handler
            result = await db.execute(
                select(TaskDB).where(TaskDB.task_id == task_id)
            )
            task_db = result.scalar_one_or_none()
            assert task_db is not None, "Task should exist in database"
            
            source_metadata = json.loads(task_db.source_metadata)
            assert "completion_handler" in source_metadata, "Completion handler should be registered"
            assert source_metadata["completion_handler"] == "api.webhooks.github.routes.handle_github_task_completion"
            step_tracker["task_created_with_handler"] = True
            
            # Step 6-7: Simulate task worker processing
            task_db.status = TaskStatus.COMPLETED
            task_db.result = "Review complete"
            task_db.cost_usd = 0.05
            await db.commit()
            await db.refresh(task_db)
            
            ws_hub = MagicMock(spec=WebSocketHub)
            worker = TaskWorker(ws_hub)
            
            await worker._invoke_completion_handler(
                task_db=task_db,
                message="Review complete",
                success=True,
                result="Review complete",
                error=None
            )
            
            step_tracker["worker_processed"] = True
            step_tracker["handler_called"] = True
            
            # Step 8-9: Verify comment posted
            assert mock_post_comment.called, "GitHub comment should be posted"
            call_args = mock_post_comment.call_args
            assert call_args[1]["message"] == "Review complete", "Message should be formatted correctly"
            step_tracker["comment_posted"] = True
            
            # Step 10: Verify Slack notification sent
            assert mock_slack.called, "Slack notification should be sent"
            slack_call = mock_slack.call_args
            assert slack_call[1]["task_id"] == task_id, "Slack notification should include task_id"
            assert slack_call[1]["webhook_source"] == "github", "Slack notification should specify GitHub source"
            step_tracker["slack_notified"] = True
            
            # Verify all steps completed
            assert all(step_tracker.values()), f"All steps should complete. Missing: {[k for k, v in step_tracker.items() if not v]}"


@pytest.mark.integration
class TestJiraFullProcessVerification:
    """Verify each part does its job in Jira webhook full process."""
    
    @pytest.mark.asyncio
    async def test_jira_full_process_each_part_does_its_job(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ):
        """
        Business Rule: Each part must do its job in the full Jira webhook process.
        
        Process Steps:
        1. Route receives webhook → validates signature ✅
        2. Route validates payload → matches command ✅
        3. Route creates task → registers completion handler ✅
        4. Route queues task → returns HTTP response ✅
        5. Task worker picks up task → processes ✅
        6. Task worker calls completion handler ✅
        7. Completion handler formats message (clean, no emoji) ✅
        8. Completion handler posts Jira comment ✅
        9. Completion handler sends Slack notification ✅
        
        Note: Jira webhook works with comments containing @agent prefix.
        """
        monkeypatch.setenv("JIRA_WEBHOOK_SECRET", "test-secret")
        
        # Jira works with comments containing @agent
        payload = {
            "webhookEvent": "jira:issue_comment_created",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "description": "Test"
                }
            },
            "comment": {
                "body": "@agent analyze this ticket",
                "author": {
                    "displayName": "Test User",
                    "accountType": "atlassian"
                }
            }
        }
        body = json.dumps(payload).encode()
        
        secret = "test-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        headers = {"X-Jira-Signature": signature}
        
        step_tracker = {
            "route_received": False,
            "route_validated": False,
            "task_created_with_handler": False,
            "task_queued": False,
            "worker_processed": False,
            "handler_called": False,
            "message_formatted_cleanly": False,
            "comment_posted": False,
            "slack_notified": False
        }
        
        with patch('api.webhooks.jira.utils.redis_client.push_task', new_callable=AsyncMock) as mock_queue, \
             patch('api.webhooks.jira.routes.post_jira_task_comment', new_callable=AsyncMock) as mock_post_comment, \
             patch('api.webhooks.jira.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            mock_queue.return_value = None
            mock_post_comment.return_value = True
            
            # Step 1-4: Route receives, validates, creates task
            response = await client.post(
                "/webhooks/jira",
                content=body,
                headers=headers
            )
            
            assert response.status_code in [200, 201], "Route should accept valid webhook"
            step_tracker["route_received"] = True
            step_tracker["route_validated"] = True
            
            data = response.json()
            task_id = data.get("task_id")
            
            if task_id:
                # Verify task queued
                assert mock_queue.called, "Task should be queued"
                step_tracker["task_queued"] = True
                
                # Step 3: Verify task created with completion handler
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == task_id)
                )
                task_db = result.scalar_one_or_none()
                
                if task_db:
                    source_metadata = json.loads(task_db.source_metadata)
                    assert "completion_handler" in source_metadata, "Completion handler should be registered"
                    assert source_metadata["completion_handler"] == "api.webhooks.jira.routes.handle_jira_task_completion"
                    step_tracker["task_created_with_handler"] = True
                    
                    # Step 5-6: Simulate task worker processing
                    task_db.status = TaskStatus.COMPLETED
                    task_db.result = "Analysis complete"
                    task_db.cost_usd = 0.05
                    await db.commit()
                    await db.refresh(task_db)
                    
                    ws_hub = MagicMock(spec=WebSocketHub)
                    worker = TaskWorker(ws_hub)
                    
                    await worker._invoke_completion_handler(
                        task_db=task_db,
                        message="Analysis complete",
                        success=True,
                        result="Analysis complete",
                        error=None
                    )
                    
                    step_tracker["worker_processed"] = True
                    step_tracker["handler_called"] = True
                    
                    # Step 7-8: Verify comment posted with clean formatting
                    assert mock_post_comment.called, "Jira comment should be posted"
                    call_args = mock_post_comment.call_args
                    assert call_args[1]["message"] == "Analysis complete", "Message should be clean (no emoji)"
                    assert "❌" not in call_args[1]["message"], "Jira messages should not have emoji"
                    step_tracker["message_formatted_cleanly"] = True
                    step_tracker["comment_posted"] = True
                    
                    # Step 9: Verify Slack notification sent
                    assert mock_slack.called, "Slack notification should be sent"
                    slack_call = mock_slack.call_args
                    assert slack_call[1]["webhook_source"] == "jira", "Slack notification should specify Jira source"
                    step_tracker["slack_notified"] = True
            
            # Verify all steps completed
            assert all(step_tracker.values()), f"All steps should complete. Missing: {[k for k, v in step_tracker.items() if not v]}"


@pytest.mark.integration
class TestSlackFullProcessVerification:
    """Verify each part does its job in Slack webhook full process."""
    
    @pytest.mark.asyncio
    async def test_slack_full_process_each_part_does_its_job(
        self, client: AsyncClient, db: AsyncSession
    ):
        """
        Business Rule: Each part must do its job in the full Slack webhook process.
        
        Process Steps:
        1. Route receives webhook → validates payload ✅
        2. Route sends immediate ephemeral response ✅
        3. Route creates task → registers completion handler ✅
        4. Route queues task → returns HTTP response ✅
        5. Task worker picks up task → processes ✅
        6. Task worker calls completion handler ✅
        7. Completion handler formats message (clean, no emoji) ✅
        8. Completion handler posts Slack message ✅
        9. Completion handler sends Slack notification ✅
        """
        payload = {
            "event": {
                "type": "app_mention",
                "text": "<@U123456> @agent help me",
                "user": "U123456",
                "channel": "C123456",
                "ts": "1234567890.123456"
            }
        }
        
        step_tracker = {
            "route_received": False,
            "route_validated": False,
            "immediate_response_sent": False,
            "task_created_with_handler": False,
            "task_queued": False,
            "worker_processed": False,
            "handler_called": False,
            "message_formatted_cleanly": False,
            "slack_message_posted": False,
            "slack_notified": False
        }
        
        with patch('api.webhooks.slack.utils.slack_client.post_ephemeral', new_callable=AsyncMock) as mock_ephemeral, \
             patch('api.webhooks.slack.utils.redis_client.push_task', new_callable=AsyncMock) as mock_queue, \
             patch('api.webhooks.slack.routes.post_slack_task_comment', new_callable=AsyncMock) as mock_post_message, \
             patch('api.webhooks.slack.routes.send_slack_notification', new_callable=AsyncMock) as mock_slack:
            
            mock_ephemeral.return_value = True
            mock_queue.return_value = None
            mock_post_message.return_value = True
            
            # Step 1-4: Route receives, validates, creates task
            response = await client.post(
                "/webhooks/slack",
                json=payload
            )
            
            assert response.status_code in [200, 201], "Route should accept valid webhook"
            step_tracker["route_received"] = True
            step_tracker["route_validated"] = True
            
            data = response.json()
            task_id = data.get("task_id")
            
            if task_id:
                # Verify immediate response sent
                assert mock_ephemeral.called, "Immediate ephemeral response should be sent"
                step_tracker["immediate_response_sent"] = True
                
                # Verify task queued
                assert mock_queue.called, "Task should be queued"
                step_tracker["task_queued"] = True
                
                # Step 3: Verify task created with completion handler
                result = await db.execute(
                    select(TaskDB).where(TaskDB.task_id == task_id)
                )
                task_db = result.scalar_one_or_none()
                
                if task_db:
                    source_metadata = json.loads(task_db.source_metadata)
                    assert "completion_handler" in source_metadata, "Completion handler should be registered"
                    assert source_metadata["completion_handler"] == "api.webhooks.slack.routes.handle_slack_task_completion"
                    step_tracker["task_created_with_handler"] = True
                    
                    # Step 5-6: Simulate task worker processing
                    task_db.status = TaskStatus.COMPLETED
                    task_db.result = "Help response"
                    task_db.cost_usd = 0.05
                    await db.commit()
                    await db.refresh(task_db)
                    
                    ws_hub = MagicMock(spec=WebSocketHub)
                    worker = TaskWorker(ws_hub)
                    
                    await worker._invoke_completion_handler(
                        task_db=task_db,
                        message="Help response",
                        success=True,
                        result="Help response",
                        error=None
                    )
                    
                    step_tracker["worker_processed"] = True
                    step_tracker["handler_called"] = True
                    
                    # Step 7-8: Verify Slack message posted with clean formatting
                    assert mock_post_message.called, "Slack message should be posted"
                    call_args = mock_post_message.call_args
                    assert call_args[1]["message"] == "Help response", "Message should be clean (no emoji)"
                    assert "❌" not in call_args[1]["message"], "Slack messages should not have emoji"
                    step_tracker["message_formatted_cleanly"] = True
                    step_tracker["slack_message_posted"] = True
                    
                    # Step 9: Verify Slack notification sent
                    assert mock_slack.called, "Slack notification should be sent"
                    slack_call = mock_slack.call_args
                    assert slack_call[1]["webhook_source"] == "slack", "Slack notification should specify Slack source"
                    step_tracker["slack_notified"] = True
            
            # Verify all steps completed
            assert all(step_tracker.values()), f"All steps should complete. Missing: {[k for k, v in step_tracker.items() if not v]}"
