import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent-container"))

from core.agents.brain import BrainAgent
from core.agents.models import AgentTask, AgentContext, AgentResult


@pytest.fixture
def brain_agent():
    return BrainAgent()


@pytest.fixture
def mock_executor():
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value=AgentResult(
        success=True,
        output="Task completed",
        model_used="claude-3-5-sonnet-20241022",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        duration_seconds=1.5,
    ))
    return executor


@pytest.fixture
def github_task():
    return AgentTask(
        task_id="task-123",
        provider="github",
        event_type="pull_request.opened",
        installation_id="inst-123",
        organization_id="org-123",
        input_message="Review PR #42",
        source_metadata={
            "repo": "owner/repo",
            "pr_number": "42",
        },
        priority=2,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def agent_context(github_task):
    return AgentContext(
        task=github_task,
        conversation_history=[],
        repository_path="/tmp/repo",
    )


@pytest.mark.asyncio
async def test_brain_agent_validation(brain_agent, github_task, agent_context):
    result = await brain_agent.validate_input(github_task, agent_context)
    assert result is True


@pytest.mark.asyncio
async def test_brain_agent_validation_fails_without_task_id(brain_agent):
    task = AgentTask(
        task_id="",
        provider="github",
        event_type="test",
        installation_id="inst-123",
        organization_id="org-123",
        input_message="Test",
        source_metadata={},
        priority=2,
        created_at=datetime.now(timezone.utc),
    )
    context = AgentContext(
        task=task,
        conversation_history=[],
        repository_path="/tmp/repo",
    )
    result = await brain_agent.validate_input(task, context)
    assert result is False


@pytest.mark.asyncio
async def test_analyze_task_type_github_review(brain_agent):
    task = AgentTask(
        task_id="task-123",
        provider="github",
        event_type="pull_request.opened",
        installation_id="inst-123",
        organization_id="org-123",
        input_message="Review this PR",
        source_metadata={},
        priority=2,
        created_at=datetime.now(timezone.utc),
    )

    task_type = await brain_agent._analyze_task_type(task)
    assert task_type == "code_review"


@pytest.mark.asyncio
async def test_analyze_task_type_jira(brain_agent):
    task = AgentTask(
        task_id="task-123",
        provider="jira",
        event_type="issue_created",
        installation_id="inst-123",
        organization_id="org-123",
        input_message="Analyze this issue",
        source_metadata={},
        priority=2,
        created_at=datetime.now(timezone.utc),
    )

    task_type = await brain_agent._analyze_task_type(task)
    assert task_type == "issue_analysis"


@pytest.mark.asyncio
async def test_analyze_task_type_slack(brain_agent):
    task = AgentTask(
        task_id="task-123",
        provider="slack",
        event_type="message",
        installation_id="inst-123",
        organization_id="org-123",
        input_message="Help me with this",
        source_metadata={},
        priority=2,
        created_at=datetime.now(timezone.utc),
    )

    task_type = await brain_agent._analyze_task_type(task)
    assert task_type == "slack_inquiry"


@pytest.mark.asyncio
async def test_create_plan_code_review(brain_agent, github_task):
    plan = await brain_agent.create_plan(github_task)

    assert plan.task_id == github_task.task_id
    assert len(plan.steps) == 3
    assert plan.steps[0].action == "analyze"
    assert plan.steps[1].action == "verify"
    assert plan.steps[2].action == "post"


@pytest.mark.asyncio
async def test_execute_with_mock_executor(brain_agent, github_task, agent_context, mock_executor):
    brain_agent.executor_agent = mock_executor

    result = await brain_agent.execute(github_task, agent_context)

    assert result.success is True
    assert result.output == "Task completed"
    assert result.metadata["orchestrated_by"] == "brain"


@pytest.mark.asyncio
async def test_execute_direct_without_executor(brain_agent, github_task, agent_context):
    result = await brain_agent.execute(github_task, agent_context)

    assert result.success is True
    assert result.model_used == "direct"
