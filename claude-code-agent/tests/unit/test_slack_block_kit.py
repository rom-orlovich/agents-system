"""TDD tests for Slack Block Kit message building."""

import pytest


class TestSlackBlockKitBuilding:
    """Test Block Kit message block construction."""
    
    def test_build_task_completion_blocks_with_buttons(self):
        """
        Business Rule: Build Block Kit blocks with interactive buttons for approval tasks.
        Behavior: Returns blocks array with Approve/Review/Reject buttons when requires_approval=True.
        """
        from api.webhooks.slack.utils import build_task_completion_blocks
        
        summary = {
            "summary": "Task completed successfully",
            "what_was_done": "Fixed bug",
            "key_insights": "Found root cause",
            "classification": "WORKFLOW"
        }
        
        routing = {
            "channel": "C123456",
            "thread_ts": "1234567890.123456",
            "repo": "owner/repo",
            "pr_number": 42,
            "ticket_key": "PROJ-123"
        }
        
        blocks = build_task_completion_blocks(
            summary=summary,
            routing=routing,
            requires_approval=True,
            task_id="task-abc123",
            cost_usd=0.05
        )
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        
        # Find actions block with buttons
        actions_block = next((b for b in blocks if b.get("type") == "actions"), None)
        assert actions_block is not None
        assert len(actions_block["elements"]) == 3
        
        button_ids = [btn["action_id"] for btn in actions_block["elements"]]
        assert "approve_task" in button_ids
        assert "review_task" in button_ids
        assert "reject_task" in button_ids
    
    def test_build_task_completion_blocks_without_buttons(self):
        """
        Business Rule: Build Block Kit blocks without buttons for non-approval tasks.
        Behavior: Returns blocks array without action buttons when requires_approval=False.
        """
        from api.webhooks.slack.utils import build_task_completion_blocks
        
        summary = {
            "summary": "Task completed",
            "what_was_done": "",
            "key_insights": "",
            "classification": "SIMPLE"
        }
        
        routing = {
            "channel": "C123456",
            "thread_ts": "1234567890.123456"
        }
        
        blocks = build_task_completion_blocks(
            summary=summary,
            routing=routing,
            requires_approval=False,
            task_id="task-xyz789",
            cost_usd=0.0
        )
        
        # Should not have actions block
        actions_blocks = [b for b in blocks if b.get("type") == "actions"]
        assert len(actions_blocks) == 0
        
        # Should have header and summary sections
        assert blocks[0]["type"] == "header"
    
    def test_build_task_completion_blocks_truncated_results(self):
        """
        Business Rule: Handle long results with truncation.
        Behavior: Truncates long text sections intelligently.
        """
        from api.webhooks.slack.utils import build_task_completion_blocks
        
        summary = {
            "summary": "Task completed",
            "what_was_done": "A" * 5000,  # Very long text
            "key_insights": "B" * 3000,
            "classification": "WORKFLOW"
        }
        
        routing = {
            "channel": "C123456",
            "thread_ts": "1234567890.123456"
        }
        
        blocks = build_task_completion_blocks(
            summary=summary,
            routing=routing,
            requires_approval=False,
            task_id="task-long",
            cost_usd=0.0
        )
        
        # Find what_was_done section
        what_was_done_block = next(
            (b for b in blocks if b.get("text", {}).get("text", "").startswith("*What Was Done*")),
            None
        )
        
        assert what_was_done_block is not None
        # Text should be truncated
        text = what_was_done_block["text"]["text"]
        assert len(text) < 5000
        assert "truncated" in text.lower()
    
    def test_build_task_completion_blocks_includes_cost(self):
        """
        Business Rule: Include cost information in context block.
        Behavior: Shows cost when cost_usd > 0.
        """
        from api.webhooks.slack.utils import build_task_completion_blocks
        
        summary = {
            "summary": "Task done",
            "what_was_done": "",
            "key_insights": "",
            "classification": "SIMPLE"
        }
        
        routing = {"channel": "C123"}
        
        blocks = build_task_completion_blocks(
            summary=summary,
            routing=routing,
            requires_approval=False,
            task_id="task-cost",
            cost_usd=0.1234
        )
        
        # Find context block
        context_block = next((b for b in blocks if b.get("type") == "context"), None)
        assert context_block is not None
        
        context_text = " ".join([e.get("text", "") for e in context_block["elements"]])
        assert "$0.1234" in context_text or "0.12" in context_text
    
    def test_build_task_completion_blocks_button_values(self):
        """
        Business Rule: Button values contain correct routing metadata.
        Behavior: Button value JSON includes action, task_id, command, source, and routing info.
        """
        from api.webhooks.slack.utils import build_task_completion_blocks
        import json
        
        summary = {
            "summary": "Plan created",
            "what_was_done": "",
            "key_insights": "",
            "classification": "WORKFLOW"
        }
        
        routing = {
            "channel": "C123456",
            "thread_ts": "1234567890.123456",
            "repo": "owner/repo",
            "pr_number": 42,
            "ticket_key": "PROJ-123"
        }
        
        blocks = build_task_completion_blocks(
            summary=summary,
            routing=routing,
            requires_approval=True,
            task_id="task-abc123",
            command="plan",
            source="github",
            cost_usd=0.0
        )
        
        actions_block = next((b for b in blocks if b.get("type") == "actions"), None)
        approve_button = next(
            (btn for btn in actions_block["elements"] if btn["action_id"] == "approve_task"),
            None
        )
        
        assert approve_button is not None
        button_value = json.loads(approve_button["value"])
        
        assert button_value["action"] == "approve"
        assert button_value["original_task_id"] == "task-abc123"
        assert button_value["command"] == "plan"
        assert button_value["source"] == "github"
        assert button_value["routing"]["repo"] == "owner/repo"
        assert button_value["routing"]["pr_number"] == 42
