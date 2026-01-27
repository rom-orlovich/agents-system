"""Tests for flow tracking functionality (TDD Phase 0)."""

from core.webhook_engine import generate_flow_id


class TestFlowIdGeneration:
    """Test flow_id generation from external IDs."""
    
    def test_generate_flow_id_from_jira_ticket(self):
        """Test: When webhook creates first task, flow_id is generated from external_id."""
        external_id = "jira:PROJ-123"
        flow_id = generate_flow_id(external_id)
        
        assert flow_id is not None
        assert isinstance(flow_id, str)
        assert len(flow_id) > 0
        # Same external_id should generate same flow_id
        assert generate_flow_id(external_id) == flow_id
    
    def test_generate_flow_id_from_github_pr(self):
        """Test: flow_id generation works for GitHub PRs."""
        external_id = "github:pr:owner/repo#42"
        flow_id = generate_flow_id(external_id)
        
        assert flow_id is not None
        assert isinstance(flow_id, str)
        # Same external_id should generate same flow_id
        assert generate_flow_id(external_id) == flow_id
    
    def test_different_external_ids_generate_different_flow_ids(self):
        """Test: Different external_ids generate different flow_ids."""
        flow_id_1 = generate_flow_id("jira:PROJ-123")
        flow_id_2 = generate_flow_id("jira:PROJ-456")
        flow_id_3 = generate_flow_id("github:pr:owner/repo#42")
        
        assert flow_id_1 != flow_id_2
        assert flow_id_1 != flow_id_3
        assert flow_id_2 != flow_id_3
    
    def test_flow_id_consistency(self):
        """Test: flow_id remains consistent across multiple calls."""
        external_id = "jira:PROJ-123"
        flow_ids = [generate_flow_id(external_id) for _ in range(10)]
        
        # All should be the same
        assert len(set(flow_ids)) == 1
    
    def test_flow_id_with_none_external_id(self):
        """Test: flow_id generation handles None external_id."""
        flow_id = generate_flow_id(None)
        
        # Should still generate a flow_id (for fallback cases)
        assert flow_id is not None
        assert isinstance(flow_id, str)


class TestFlowIdPropagation:
    """Test flow_id propagation through task hierarchy."""
    async def test_child_task_inherits_parent_flow_id(self, db):
        """Test: When child task is created, it inherits parent's flow_id automatically."""
        from core.database.models import TaskDB, SessionDB
        from datetime import datetime, timezone
        import json
        
        # Create parent task with flow_id
        session = SessionDB(
            session_id="session-inherit-test",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()  # Flush to ensure session is created before tasks
        
        parent_task = TaskDB(
            task_id="task-parent",
            session_id="session-inherit-test",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Parent task",
            source="webhook",
            source_metadata=json.dumps({
                "flow_id": "flow-123",
                "initiated_task_id": "task-parent"
            })
        )
        db.add(parent_task)
        await db.commit()
        
        # Simulate creating child task - should inherit flow_id
        parent_metadata = json.loads(parent_task.source_metadata)
        child_flow_id = parent_metadata.get("flow_id")
        
        assert child_flow_id == "flow-123"
    async def test_flow_id_propagates_across_task_chain(self, db):
        """Test: flow_id remains consistent across entire task flow."""
        from core.database.models import TaskDB, SessionDB
        from datetime import datetime, timezone
        import json
        
        # Use unique session ID for this test
        session = SessionDB(
            session_id="session-flow-test",
            user_id="user-001",
            machine_id="machine-001",
            connected_at=datetime.now(timezone.utc)
        )
        db.add(session)
        await db.flush()  # Flush to ensure session is created before tasks
        
        flow_id = "flow-abc123"
        initiated_task_id = "task-root"
        
        # Create root task
        root_task = TaskDB(
            task_id=initiated_task_id,
            session_id="session-flow-test",
            user_id="user-001",
            agent_type="planning",
            status="queued",
            input_message="Root task",
            source="webhook",
            source_metadata=json.dumps({
                "flow_id": flow_id,
                "initiated_task_id": initiated_task_id
            })
        )
        db.add(root_task)
        
        # Create child task
        child_task = TaskDB(
            task_id="task-child",
            session_id="session-flow-test",
            user_id="user-001",
            agent_type="executor",
            status="queued",
            input_message="Child task",
            source="webhook",
            parent_task_id=initiated_task_id,
            source_metadata=json.dumps({
                "flow_id": flow_id,  # Inherited from parent
                "initiated_task_id": initiated_task_id  # Same root
            })
        )
        db.add(child_task)
        
        # Create grandchild task
        grandchild_task = TaskDB(
            task_id="task-grandchild",
            session_id="session-flow-test",
            user_id="user-001",
            agent_type="executor",
            status="queued",
            input_message="Grandchild task",
            source="webhook",
            parent_task_id="task-child",
            source_metadata=json.dumps({
                "flow_id": flow_id,  # Still same flow_id
                "initiated_task_id": initiated_task_id  # Still same root
            })
        )
        db.add(grandchild_task)
        await db.commit()
        
        # Verify all tasks share same flow_id
        root_metadata = json.loads(root_task.source_metadata)
        child_metadata = json.loads(child_task.source_metadata)
        grandchild_metadata = json.loads(grandchild_task.source_metadata)
        
        assert root_metadata["flow_id"] == flow_id
        assert child_metadata["flow_id"] == flow_id
        assert grandchild_metadata["flow_id"] == flow_id
        assert root_metadata["initiated_task_id"] == initiated_task_id
        assert child_metadata["initiated_task_id"] == initiated_task_id
        assert grandchild_metadata["initiated_task_id"] == initiated_task_id
