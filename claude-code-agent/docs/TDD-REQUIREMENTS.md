# TDD Requirements - Multi-Subagent Orchestration System

> **Philosophy:** Tests verify **business outcomes** (what the system does), NOT implementation details (how it does it). Internal refactoring should not break these tests.

---

## Table of Contents

1. [Part 2: Multi-Subagent Orchestration](#part-2-multi-subagent-orchestration)
2. [Part 3: Webhook Routes & Container Management](#part-3-webhook-routes--container-management)
3. [Part 4B: Real-Time Logging & Monitoring](#part-4b-real-time-logging--monitoring)
4. [Part 5: Data Persistence](#part-5-data-persistence)
5. [Part 6: Security & Permissions](#part-6-security--permissions)
6. [Part 8: Multi-Account & Machine Management](#part-8-multi-account--machine-management)
7. [Part 9: Session Status & Cost Tracking](#part-9-session-status--cost-tracking)

---

## Part 2: Multi-Subagent Orchestration

### 2.1 Subagent Spawn/Stop Tests

```python
# tests/integration/test_subagent_orchestration.py

class TestSubagentSpawnFlow:
    """Test subagent spawn business requirements."""
    
    async def test_spawn_foreground_subagent_becomes_active(self, client):
        """
        REQUIREMENT: When Brain spawns a foreground subagent,
        it should appear in active subagents list with 'running' status.
        """
        response = await client.post("/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground",
            "task_id": "task-123"
        })
        
        assert response.status_code == 200
        subagent_id = response.json()["data"]["subagent_id"]
        
        # Verify it's in active list
        active = await client.get("/subagents/active")
        assert any(s["subagent_id"] == subagent_id for s in active.json())
    
    async def test_spawn_background_subagent_runs_async(self, client):
        """
        REQUIREMENT: Background subagents should run without blocking
        and auto-deny permission requests.
        """
        response = await client.post("/subagents/spawn", json={
            "agent_type": "executor",
            "mode": "background",
            "task_id": "task-456"
        })
        
        assert response.status_code == 200
        assert response.json()["data"]["mode"] == "background"
        assert response.json()["data"]["permission_mode"] == "auto-deny"
    
    async def test_stop_subagent_terminates_and_removes(self, client, running_subagent):
        """
        REQUIREMENT: Stopping a subagent should terminate it
        and remove it from active list.
        """
        subagent_id = running_subagent["subagent_id"]
        
        response = await client.post(f"/subagents/{subagent_id}/stop")
        assert response.status_code == 200
        
        # Verify removed from active list
        active = await client.get("/subagents/active")
        assert not any(s["subagent_id"] == subagent_id for s in active.json())
    
    async def test_max_parallel_subagents_enforced(self, client):
        """
        REQUIREMENT: System should enforce maximum of 10 parallel subagents.
        """
        # Spawn 10 subagents
        for i in range(10):
            await client.post("/subagents/spawn", json={
                "agent_type": "planning",
                "mode": "background",
                "task_id": f"task-{i}"
            })
        
        # 11th should fail
        response = await client.post("/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "background",
            "task_id": "task-overflow"
        })
        
        assert response.status_code == 429
        assert "maximum" in response.json()["detail"].lower()


class TestParallelExecutionFlow:
    """Test parallel subagent execution requirements."""
    
    async def test_parallel_group_executes_concurrently(self, client):
        """
        REQUIREMENT: Subagents in a parallel group should execute
        concurrently, not sequentially.
        """
        start_time = datetime.utcnow()
        
        response = await client.post("/subagents/parallel", json={
            "agents": [
                {"type": "planning", "task": "Research auth module"},
                {"type": "planning", "task": "Research database module"},
                {"type": "planning", "task": "Research API module"},
            ]
        })
        
        # Wait for completion
        group_id = response.json()["data"]["group_id"]
        await wait_for_group_completion(client, group_id, timeout=120)
        
        elapsed = (datetime.utcnow() - start_time).seconds
        
        # If sequential, would take ~3x longer
        # Parallel should complete in roughly the time of the longest task
        assert elapsed < 90  # Assuming each task takes ~30s
    
    async def test_parallel_results_aggregated(self, client, completed_parallel_group):
        """
        REQUIREMENT: Results from parallel subagents should be
        aggregated and accessible together.
        """
        group_id = completed_parallel_group["group_id"]
        
        results = await client.get(f"/subagents/parallel/{group_id}/results")
        
        assert results.status_code == 200
        assert len(results.json()["results"]) == 3
        for result in results.json()["results"]:
            assert "output" in result
            assert "status" in result
```

### 2.2 Context Management Tests

```python
# tests/integration/test_context_management.py

class TestSubagentContextFlow:
    """Test subagent context sharing requirements."""
    
    async def test_subagent_receives_conversation_context(self, client, conversation_with_history):
        """
        REQUIREMENT: Subagent should receive last 20 messages
        from conversation as context.
        """
        conv_id = conversation_with_history["conversation_id"]
        
        response = await client.post("/subagents/spawn", json={
            "agent_type": "planning",
            "mode": "foreground",
            "conversation_id": conv_id
        })
        
        subagent_id = response.json()["data"]["subagent_id"]
        context = await client.get(f"/subagents/{subagent_id}/context")
        
        assert context.json()["message_count"] <= 20
        assert context.json()["conversation_id"] == conv_id
    
    async def test_subagent_context_isolated_between_tasks(self, client):
        """
        REQUIREMENT: Each subagent's context should be isolated;
        one subagent's work shouldn't leak to another.
        """
        # Spawn two subagents for different tasks
        sub1 = await client.post("/subagents/spawn", json={
            "agent_type": "planning",
            "task_id": "task-secret-a"
        })
        sub2 = await client.post("/subagents/spawn", json={
            "agent_type": "planning", 
            "task_id": "task-secret-b"
        })
        
        ctx1 = await client.get(f"/subagents/{sub1.json()['data']['subagent_id']}/context")
        ctx2 = await client.get(f"/subagents/{sub2.json()['data']['subagent_id']}/context")
        
        # Contexts should not contain each other's task info
        assert "task-secret-b" not in str(ctx1.json())
        assert "task-secret-a" not in str(ctx2.json())
```

---

## Part 3: Webhook Routes & Container Management

### 3.1 Webhook Creation Tests

```python
# tests/integration/test_webhook_creation.py

class TestWebhookCreationFlow:
    """Test webhook creation business requirements."""
    
    async def test_create_webhook_with_immediate_feedback(self, client):
        """
        REQUIREMENT: Created webhooks MUST have at least one
        immediate feedback action (priority 0 or 1).
        """
        response = await client.post("/webhooks", json={
            "name": "github-issues",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "react",
                    "priority": 0,  # Immediate feedback
                    "template": "👀"
                },
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "priority": 10,
                    "template": "Analyze issue: {{title}}"
                }
            ]
        })
        
        assert response.status_code == 200
        webhook_id = response.json()["data"]["webhook_id"]
        
        # Verify immediate feedback exists
        webhook = await client.get(f"/webhooks/{webhook_id}")
        commands = webhook.json()["commands"]
        has_immediate = any(c["priority"] <= 1 for c in commands)
        assert has_immediate
    
    async def test_webhook_without_feedback_rejected(self, client):
        """
        REQUIREMENT: Webhooks without immediate feedback should
        be rejected with validation error.
        """
        response = await client.post("/webhooks", json={
            "name": "bad-webhook",
            "provider": "github",
            "commands": [
                {
                    "trigger": "issues.opened",
                    "action": "create_task",
                    "priority": 10,  # No immediate feedback!
                    "template": "Do something"
                }
            ]
        })
        
        assert response.status_code == 400
        assert "immediate feedback" in response.json()["detail"].lower()
    
    async def test_webhook_secret_stored_encrypted(self, client, db):
        """
        REQUIREMENT: Webhook secrets should be stored encrypted,
        not in plaintext.
        """
        response = await client.post("/webhooks", json={
            "name": "secure-webhook",
            "provider": "github",
            "secret": "my-secret-key-123",
            "commands": [{"trigger": "push", "action": "react", "priority": 0}]
        })
        
        webhook_id = response.json()["data"]["webhook_id"]
        
        # Check raw database value
        raw = await db.execute(
            "SELECT secret FROM webhook_configs WHERE webhook_id = ?",
            [webhook_id]
        )
        stored_secret = raw.fetchone()[0]
        
        assert stored_secret != "my-secret-key-123"  # Not plaintext
        assert len(stored_secret) > 50  # Looks encrypted


class TestWebhookExecutionFlow:
    """Test webhook execution business requirements."""
    
    async def test_webhook_immediate_feedback_sent_first(self, client, github_webhook):
        """
        REQUIREMENT: Immediate feedback (priority 0-1) should be
        sent BEFORE task creation (priority 10+).
        """
        execution_log = []
        
        # Mock to capture execution order
        with patch_webhook_actions(execution_log):
            await client.post(f"/webhooks/github", json={
                "action": "opened",
                "issue": {"number": 1, "title": "Test"}
            })
        
        # Verify order
        feedback_idx = next(i for i, a in enumerate(execution_log) if a["action"] == "react")
        task_idx = next(i for i, a in enumerate(execution_log) if a["action"] == "create_task")
        
        assert feedback_idx < task_idx
    
    async def test_webhook_feedback_within_5_seconds(self, client, github_webhook):
        """
        REQUIREMENT: Immediate feedback should arrive within 5 seconds.
        """
        start = datetime.utcnow()
        
        with capture_github_api_calls() as calls:
            await client.post(f"/webhooks/github", json={
                "action": "opened",
                "issue": {"number": 1, "title": "Test"}
            })
        
        # Find the reaction call
        reaction_call = next(c for c in calls if "reactions" in c["url"])
        elapsed = (reaction_call["timestamp"] - start).total_seconds()
        
        assert elapsed < 5
```

### 3.2 Container Management Tests

```python
# tests/integration/test_container_management.py

class TestContainerManagementFlow:
    """Test container management business requirements."""
    
    async def test_list_container_processes(self, client):
        """
        REQUIREMENT: Should be able to list all running processes
        in the container.
        """
        response = await client.get("/container/processes")
        
        assert response.status_code == 200
        processes = response.json()["processes"]
        
        # Should at least have the API server process
        assert len(processes) > 0
        assert all("pid" in p and "name" in p for p in processes)
    
    async def test_container_resource_usage(self, client):
        """
        REQUIREMENT: Should report CPU and memory usage.
        """
        response = await client.get("/container/resources")
        
        assert response.status_code == 200
        resources = response.json()
        
        assert "cpu_percent" in resources
        assert "memory_mb" in resources
        assert 0 <= resources["cpu_percent"] <= 100
    
    async def test_kill_process_requires_allowlist(self, client):
        """
        REQUIREMENT: Killing processes should only work for
        processes in the explicit allowlist.
        """
        # Try to kill a system process (not allowed)
        response = await client.post("/container/processes/1/kill")
        
        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"].lower()
```

---

## Part 4B: Real-Time Logging & Monitoring

### 4B.1 WebSocket Streaming Tests

```python
# tests/integration/test_realtime_logging.py

class TestRealtimeLoggingFlow:
    """Test real-time logging business requirements."""
    
    async def test_subagent_output_streams_via_websocket(self, client, ws_client):
        """
        REQUIREMENT: Subagent output should stream in real-time
        via WebSocket, not just at completion.
        """
        received_chunks = []
        
        async def collect_chunks():
            async for msg in ws_client.subscribe("/ws/subagents/output"):
                received_chunks.append(msg)
                if len(received_chunks) >= 5:
                    break
        
        # Start collecting in background
        collector = asyncio.create_task(collect_chunks())
        
        # Spawn a subagent that produces output
        await client.post("/subagents/spawn", json={
            "agent_type": "planning",
            "task_id": "streaming-test"
        })
        
        await asyncio.wait_for(collector, timeout=30)
        
        # Should have received multiple chunks, not just final result
        assert len(received_chunks) >= 3
    
    async def test_parallel_subagents_stream_separately(self, client, ws_client):
        """
        REQUIREMENT: Output from parallel subagents should be
        distinguishable by subagent_id.
        """
        messages = []
        
        async def collect():
            async for msg in ws_client.subscribe("/ws/subagents/output"):
                messages.append(msg)
                if len(messages) >= 10:
                    break
        
        collector = asyncio.create_task(collect())
        
        # Spawn parallel subagents
        await client.post("/subagents/parallel", json={
            "agents": [
                {"type": "planning", "task": "Task A"},
                {"type": "planning", "task": "Task B"},
            ]
        })
        
        await asyncio.wait_for(collector, timeout=60)
        
        # Messages should have subagent_id to distinguish them
        subagent_ids = set(m["subagent_id"] for m in messages)
        assert len(subagent_ids) >= 2
    
    async def test_websocket_reconnect_resumes_stream(self, client, ws_client):
        """
        REQUIREMENT: Reconnecting to WebSocket should resume
        streaming from where it left off (or provide recent history).
        """
        # Start a long-running task
        task = await client.post("/subagents/spawn", json={
            "agent_type": "planning",
            "task_id": "long-task"
        })
        subagent_id = task.json()["data"]["subagent_id"]
        
        # Connect, get some messages, disconnect
        first_messages = []
        async for msg in ws_client.subscribe(f"/ws/subagents/{subagent_id}/output"):
            first_messages.append(msg)
            if len(first_messages) >= 3:
                break
        
        # Reconnect
        reconnect_messages = []
        async for msg in ws_client.subscribe(f"/ws/subagents/{subagent_id}/output"):
            reconnect_messages.append(msg)
            if len(reconnect_messages) >= 3:
                break
        
        # Should get continuation or recent history, not start from scratch
        # (Implementation may vary - could be sequence numbers or timestamps)
        assert len(reconnect_messages) > 0
```

---

## Part 5: Data Persistence

### 5.1 Persistence Tests

```python
# tests/integration/test_data_persistence.py

class TestDataPersistenceFlow:
    """Test data persistence business requirements."""
    
    async def test_task_survives_restart(self, client, restart_server):
        """
        REQUIREMENT: Tasks should persist across server restarts.
        """
        # Create a task
        task = await client.post("/tasks", json={"message": "Test task"})
        task_id = task.json()["data"]["task_id"]
        
        # Restart server
        await restart_server()
        
        # Task should still exist
        response = await client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["task_id"] == task_id
    
    async def test_webhook_config_persists(self, client, restart_server):
        """
        REQUIREMENT: Webhook configurations should persist.
        """
        webhook = await client.post("/webhooks", json={
            "name": "persistent-webhook",
            "provider": "github",
            "commands": [{"trigger": "push", "action": "react", "priority": 0}]
        })
        webhook_id = webhook.json()["data"]["webhook_id"]
        
        await restart_server()
        
        response = await client.get(f"/webhooks/{webhook_id}")
        assert response.status_code == 200
    
    async def test_conversation_history_persists(self, client, restart_server):
        """
        REQUIREMENT: Conversation history should persist.
        """
        # Create conversation with messages
        conv = await client.post("/conversations", json={"title": "Test"})
        conv_id = conv.json()["data"]["conversation_id"]
        
        await client.post(f"/conversations/{conv_id}/messages", json={
            "role": "user",
            "content": "Hello"
        })
        
        await restart_server()
        
        messages = await client.get(f"/conversations/{conv_id}/messages")
        assert len(messages.json()) == 1
        assert messages.json()[0]["content"] == "Hello"
    
    async def test_redis_task_queue_recovers(self, client, restart_redis):
        """
        REQUIREMENT: Queued tasks should be recoverable after Redis restart.
        """
        # Queue a task
        task = await client.post("/tasks", json={"message": "Queued task"})
        task_id = task.json()["data"]["task_id"]
        
        # Restart Redis
        await restart_redis()
        
        # Task should be re-queued or marked for retry
        status = await client.get(f"/tasks/{task_id}")
        assert status.json()["status"] in ["queued", "pending_retry"]
```

---

## Part 6: Security & Permissions

### 6.1 Permission Tests

```python
# tests/integration/test_security_permissions.py

class TestSecurityPermissionsFlow:
    """Test security and permission business requirements."""
    
    async def test_webhook_creation_requires_approval(self, client):
        """
        REQUIREMENT: Creating webhooks should require user approval
        (not auto-approved).
        """
        response = await client.post("/webhooks", json={
            "name": "needs-approval",
            "provider": "github",
            "commands": [{"trigger": "push", "action": "react", "priority": 0}]
        })
        
        # Should return pending approval status, not immediate creation
        assert response.json()["data"]["status"] == "pending_approval"
    
    async def test_agent_creation_requires_brain_approval(self, client):
        """
        REQUIREMENT: Creating new agents should require Brain approval.
        """
        response = await client.post("/agents", json={
            "name": "new-agent",
            "description": "A new agent",
            "tools": ["Read", "Edit"]
        })
        
        assert response.json()["data"]["status"] == "pending_brain_approval"
    
    async def test_container_exec_requires_allowlist(self, client):
        """
        REQUIREMENT: Container exec commands must be in allowlist.
        """
        # Try to run arbitrary command
        response = await client.post("/container/exec", json={
            "command": "rm -rf /"
        })
        
        assert response.status_code == 403
        assert "not in allowlist" in response.json()["detail"].lower()
    
    async def test_audit_log_records_all_actions(self, client, db):
        """
        REQUIREMENT: All sensitive actions should be logged to audit trail.
        """
        # Perform some actions
        await client.post("/webhooks", json={...})
        await client.post("/subagents/spawn", json={...})
        
        # Check audit log
        logs = await db.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10")
        
        assert len(logs.fetchall()) >= 2
        actions = [log["action"] for log in logs]
        assert "webhook_create" in actions
        assert "subagent_spawn" in actions
```

---

## Part 8: Multi-Account & Machine Management

> See main plan document `MULTI-SUBAGENT-ORCHESTRATION-PLAN.md` section 8.6 for these tests.

---

## Part 9: Session Status & Cost Tracking

### 9.1 Cost Calculation Tests

```python
# tests/integration/test_cost_tracking.py

class TestCostTrackingFlow:
    """Test cost tracking business requirements."""
    
    async def test_task_cost_calculated_from_tokens(self, client):
        """
        REQUIREMENT: Task cost should be calculated from input/output tokens
        using Claude's pricing model.
        
        Current pricing (as of 2024):
        - Claude 3.5 Sonnet: $3/1M input, $15/1M output
        - Claude 3 Opus: $15/1M input, $75/1M output
        """
        # Complete a task
        task = await client.post("/chat", json={"message": "Hello"})
        task_id = task.json()["data"]["task_id"]
        
        await wait_for_task_completion(client, task_id)
        
        result = await client.get(f"/tasks/{task_id}")
        
        # Verify cost is calculated
        assert result.json()["cost_usd"] > 0
        assert result.json()["input_tokens"] > 0
        assert result.json()["output_tokens"] > 0
        
        # Verify cost formula (approximately)
        # cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
        expected_cost = (
            result.json()["input_tokens"] * 3 +
            result.json()["output_tokens"] * 15
        ) / 1_000_000
        
        assert abs(result.json()["cost_usd"] - expected_cost) < 0.01
    
    async def test_session_cost_aggregates_tasks(self, client):
        """
        REQUIREMENT: Session total cost should be sum of all task costs.
        """
        session_id = "test-session-123"
        
        # Run multiple tasks
        for i in range(3):
            await client.post("/chat", json={
                "message": f"Task {i}",
                "session_id": session_id
            })
        
        session = await client.get(f"/sessions/{session_id}")
        tasks = await client.get(f"/sessions/{session_id}/tasks")
        
        expected_total = sum(t["cost_usd"] for t in tasks.json())
        
        assert abs(session.json()["total_cost_usd"] - expected_total) < 0.001
    
    async def test_daily_cost_aggregation(self, client):
        """
        REQUIREMENT: Analytics should show daily cost breakdown.
        """
        response = await client.get("/analytics/costs/daily?days=7")
        
        assert response.status_code == 200
        assert "dates" in response.json()
        assert "costs" in response.json()
        assert len(response.json()["dates"]) <= 7


class TestSessionStatusFlow:
    """Test session status business requirements."""
    
    async def test_session_shows_active_status(self, client):
        """
        REQUIREMENT: Active sessions should show 'active' status
        with current task count.
        """
        session_id = "active-session"
        
        # Start a task
        await client.post("/chat", json={
            "message": "Long running task",
            "session_id": session_id
        })
        
        status = await client.get(f"/sessions/{session_id}/status")
        
        assert status.json()["status"] == "active"
        assert status.json()["running_tasks"] >= 1
    
    async def test_session_reset_clears_context(self, client):
        """
        REQUIREMENT: Resetting a session should clear conversation
        context but preserve cost history.
        """
        session_id = "reset-test-session"
        
        # Build up some history
        await client.post("/chat", json={
            "message": "Remember this",
            "session_id": session_id
        })
        
        original_cost = (await client.get(f"/sessions/{session_id}")).json()["total_cost_usd"]
        
        # Reset session
        await client.post(f"/sessions/{session_id}/reset")
        
        # Context should be cleared
        context = await client.get(f"/sessions/{session_id}/context")
        assert len(context.json()["messages"]) == 0
        
        # Cost should be preserved
        session = await client.get(f"/sessions/{session_id}")
        assert session.json()["total_cost_usd"] == original_cost
    
    async def test_weekly_session_summary(self, client):
        """
        REQUIREMENT: Should provide weekly session summary with
        total cost, task count, and active days.
        """
        response = await client.get("/sessions/summary/weekly")
        
        assert response.status_code == 200
        summary = response.json()
        
        assert "total_cost_usd" in summary
        assert "total_tasks" in summary
        assert "active_days" in summary
        assert "sessions" in summary
        assert summary["active_days"] <= 7


class TestSessionDisplayFlow:
    """Test session display business requirements for dashboard."""
    
    async def test_current_session_status_displayed(self, client):
        """
        REQUIREMENT: Dashboard should show current session status
        including: status, running tasks, cost, reset time.
        """
        response = await client.get("/dashboard/session/current")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "status" in data  # active, idle, disconnected
        assert "running_tasks" in data
        assert "total_cost_usd" in data
        assert "started_at" in data
        assert "last_activity" in data
    
    async def test_session_history_shows_weekly(self, client):
        """
        REQUIREMENT: Session history should show past 7 days
        with daily breakdown.
        """
        response = await client.get("/dashboard/sessions/history?days=7")
        
        assert response.status_code == 200
        history = response.json()
        
        assert "daily" in history
        assert len(history["daily"]) <= 7
        
        for day in history["daily"]:
            assert "date" in day
            assert "sessions" in day
            assert "total_cost" in day
            assert "task_count" in day
```

### 9.2 Session Status UI Requirements

```python
# tests/integration/test_session_ui_requirements.py

class TestSessionUIRequirements:
    """Test session UI display requirements."""
    
    async def test_session_card_shows_all_info(self, client):
        """
        REQUIREMENT: Session card in dashboard should display:
        - Session ID (truncated)
        - Status indicator (green=active, gray=idle, red=error)
        - Running task count
        - Total cost (formatted as $X.XX)
        - Duration (e.g., "2h 15m")
        - Reset button
        """
        # This is a UI contract test - verifies API returns all needed data
        response = await client.get("/dashboard/session/current")
        data = response.json()
        
        required_fields = [
            "session_id",
            "status",
            "running_tasks",
            "total_cost_usd",
            "started_at",
            "duration_seconds",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    async def test_weekly_chart_data_format(self, client):
        """
        REQUIREMENT: Weekly chart should receive data in Chart.js format.
        """
        response = await client.get("/analytics/costs/daily?days=7")
        data = response.json()
        
        # Chart.js format
        assert "dates" in data  # x-axis labels
        assert "costs" in data  # y-axis values
        assert "task_counts" in data  # secondary y-axis
        
        assert len(data["dates"]) == len(data["costs"])
```

---

## Test Fixtures (Shared)

```python
# tests/fixtures/orchestration_fixtures.py

@pytest.fixture
async def running_subagent(client):
    """A running subagent for testing."""
    response = await client.post("/subagents/spawn", json={
        "agent_type": "planning",
        "mode": "foreground",
        "task_id": "fixture-task"
    })
    return response.json()["data"]

@pytest.fixture
async def conversation_with_history(client, db):
    """Conversation with 25 messages (more than context limit)."""
    conv = await client.post("/conversations", json={"title": "Test"})
    conv_id = conv.json()["data"]["conversation_id"]
    
    for i in range(25):
        await client.post(f"/conversations/{conv_id}/messages", json={
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i}"
        })
    
    return {"conversation_id": conv_id}

@pytest.fixture
async def github_webhook(client):
    """Pre-configured GitHub webhook."""
    response = await client.post("/webhooks", json={
        "name": "test-github",
        "provider": "github",
        "commands": [
            {"trigger": "issues.opened", "action": "react", "priority": 0, "template": "👀"},
            {"trigger": "issues.opened", "action": "create_task", "priority": 10}
        ]
    })
    return response.json()["data"]

@pytest.fixture
async def restart_server():
    """Helper to restart the server for persistence tests."""
    async def _restart():
        # Implementation depends on test infrastructure
        pass
    return _restart
```

---

## Test Summary

| Part | Category | # Tests | Business Requirements |
|------|----------|---------|----------------------|
| **Part 2** | Subagent Orchestration | 7 | Spawn, stop, parallel, context |
| **Part 3** | Webhooks & Container | 8 | Creation, execution, feedback, processes |
| **Part 4B** | Real-time Logging | 3 | WebSocket streaming, parallel output |
| **Part 5** | Data Persistence | 4 | Tasks, webhooks, conversations, Redis |
| **Part 6** | Security | 4 | Permissions, allowlist, audit |
| **Part 8** | Multi-Account | 12 | See main plan |
| **Part 9** | Session & Cost | 10 | Cost calculation, session status, weekly |
| **Total** | | **48** | Core orchestration flows |

---

## Cost Calculation Reference

### How Costs Are Calculated

```python
# From core/cli_runner.py - costs come from Claude CLI output

# Claude CLI returns JSON with:
{
    "type": "result",
    "total_cost_usd": 0.0234,  # Total cost for this execution
    "usage": {
        "input_tokens": 1500,
        "output_tokens": 800
    }
}

# Pricing (as of 2024):
# Claude 3.5 Sonnet: $3/1M input, $15/1M output
# Claude 3 Opus: $15/1M input, $75/1M output

# Formula:
cost_usd = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
```

### Where Costs Are Stored

```python
# TaskDB model (core/database/models.py)
cost_usd = Column(Float, default=0.0)      # Per-task cost
input_tokens = Column(Integer, default=0)   # Input token count
output_tokens = Column(Integer, default=0)  # Output token count

# SessionDB model
total_cost_usd = Column(Float, default=0.0)  # Aggregated session cost
total_tasks = Column(Integer, default=0)     # Task count
```

### Analytics Endpoints

```python
# GET /analytics/summary - Today's and total costs
# GET /analytics/costs/daily?days=30 - Daily breakdown
# GET /analytics/costs/by-subagent?days=30 - Cost by agent type
```

---

## Implementation Checklist

After implementing each part, update this checklist:

- [ ] Part 2: Subagent Orchestration tests passing
- [ ] Part 3: Webhook & Container tests passing
- [ ] Part 4B: Real-time Logging tests passing
- [ ] Part 5: Data Persistence tests passing
- [ ] Part 6: Security tests passing
- [ ] Part 8: Multi-Account tests passing
- [ ] Part 9: Session & Cost tests passing

**Update main `MULTI-SUBAGENT-ORCHESTRATION-PLAN.md` when all tests pass.**
