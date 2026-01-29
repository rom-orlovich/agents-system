"""Tests for conversation inheritance functionality (TDD Phase 0)."""

import pytest
from core.webhook_engine import should_start_new_conversation


class TestConversationInheritance:
    """Test conversation inheritance rules."""
    
    def test_default_behavior_no_new_conversation(self):
        """Test: Child tasks automatically inherit parent's conversation_id (default behavior)."""
        prompt = "Please analyze this code"
        metadata = {}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is False
    
    def test_new_conversation_keyword_detected(self):
        """Test: When user says 'new conversation', child task gets new conversation_id."""
        prompt = "Let's start a new conversation about this"
        metadata = {}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is True
    
    def test_start_fresh_keyword_detected(self):
        """Test: When user says 'start fresh', child task gets new conversation_id."""
        prompt = "Start fresh and analyze this"
        metadata = {}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is True
    
    def test_new_context_keyword_detected(self):
        """Test: When user says 'new context', child task gets new conversation_id."""
        prompt = "Use a new context for this task"
        metadata = {}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is True
    
    def test_reset_conversation_keyword_detected(self):
        """Test: When user says 'reset conversation', child task gets new conversation_id."""
        prompt = "Reset conversation and start over"
        metadata = {}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is True
    
    def test_metadata_flag_new_conversation(self):
        """Test: When metadata has new_conversation: true, child task gets new conversation_id."""
        prompt = "Normal prompt"
        metadata = {"new_conversation": True}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is True
    
    def test_metadata_flag_false_no_new_conversation(self):
        """Test: When metadata has new_conversation: false, child task inherits conversation."""
        prompt = "Normal prompt"
        metadata = {"new_conversation": False}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is False
    
    def test_case_insensitive_keywords(self):
        """Test: Keywords are detected case-insensitively."""
        prompts = [
            "NEW CONVERSATION",
            "New Conversation",
            "new conversation",
            "Start Fresh",
            "START FRESH",
            "New Context",
            "NEW CONTEXT",
            "Reset Conversation",
            "RESET CONVERSATION"
        ]
        
        for prompt in prompts:
            result = should_start_new_conversation(prompt, {})
            assert result is True, f"Failed for prompt: {prompt}"
    
    def test_keyword_in_middle_of_sentence(self):
        """Test: Keywords detected even when in middle of sentence."""
        prompt = "I think we should start a new conversation about this issue"
        metadata = {}
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is True
    
    def test_metadata_flag_overrides_keywords(self):
        """Test: Metadata flag takes precedence over keywords."""
        prompt = "new conversation"  # Has keyword
        metadata = {"new_conversation": False}  # But flag says no
        
        result = should_start_new_conversation(prompt, metadata)
        assert result is False  # Flag should win
    


class TestFlowIdPropagationWithConversationBreaks:
    """Test that flow_id propagates even when conversation breaks."""
    async def test_flow_id_preserved_when_new_conversation_created(self, db):
        """Test: New conversation still linked to same flow_id for tracking."""
        from core.database.models import TaskDB, SessionDB, ConversationDB
        from datetime import datetime, timezone
        import json
        
        # Create session
        session = SessionDB(
            session_id="session-conv-break-test",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()
        
        flow_id = "flow-xyz789"
        root_task_id = "task-root-conv"
        
        # Create root task with flow_id
        root_task = TaskDB(
            task_id=root_task_id,
            session_id="session-conv-break-test",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Root task",
            source="webhook",
            source_metadata=json.dumps({
                "flow_id": flow_id,
                "initiated_task_id": root_task_id,
                "conversation_id": "conv-1"
            })
        )
        db.add(root_task)
        
        # Create child task that breaks conversation but keeps flow_id
        child_task = TaskDB(
            task_id="task-child-conv",
            session_id="session-conv-break-test",
            user_id="user-001",
            agent_type="executor",
            status="queued",
            input_message="Child task with new conversation",
            source="webhook",
            parent_task_id=root_task_id,
            source_metadata=json.dumps({
                "flow_id": flow_id,  # Same flow_id
                "initiated_task_id": root_task_id,  # Same root
                "conversation_id": "conv-2"  # Different conversation
            })
        )
        db.add(child_task)
        await db.commit()
        
        # Verify flow_id is preserved
        root_metadata = json.loads(root_task.source_metadata)
        child_metadata = json.loads(child_task.source_metadata)
        
        assert root_metadata["flow_id"] == flow_id
        assert child_metadata["flow_id"] == flow_id  # Flow ID preserved
        assert root_metadata["conversation_id"] == "conv-1"
        assert child_metadata["conversation_id"] == "conv-2"  # Different conversation
        assert root_metadata["initiated_task_id"] == root_task_id
        assert child_metadata["initiated_task_id"] == root_task_id  # Same root
