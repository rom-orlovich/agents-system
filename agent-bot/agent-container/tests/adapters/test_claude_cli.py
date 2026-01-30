from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

import pytest

from adapters.cli.claude_adapter import ClaudeCLIAdapter


@pytest.fixture
def adapter() -> ClaudeCLIAdapter:
    return ClaudeCLIAdapter(claude_binary="claude")


@pytest.mark.asyncio
async def test_execute_success(adapter: ClaudeCLIAdapter):
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(
        return_value=(b"Command output\n10 tokens used", b"")
    )

    with patch(
        "adapters.cli.claude_adapter.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        result = await adapter.execute_and_wait(
            command=["claude", "chat"],
            input_text="test prompt",
            timeout_seconds=30,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert "Command output" in result.output
        assert result.tokens_used == 10
        assert result.error is None


@pytest.mark.asyncio
async def test_execute_failure(adapter: ClaudeCLIAdapter):
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(
        return_value=(b"", b"Error occurred")
    )

    with patch(
        "adapters.cli.claude_adapter.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        result = await adapter.execute_and_wait(
            command=["claude", "chat"],
            input_text="test prompt",
            timeout_seconds=30,
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.error == "Error occurred"


@pytest.mark.asyncio
async def test_execute_timeout(adapter: ClaudeCLIAdapter):
    mock_process = AsyncMock()
    mock_process.communicate = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )
    mock_process.kill = AsyncMock()
    mock_process.wait = AsyncMock()

    with patch(
        "adapters.cli.claude_adapter.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        result = await adapter.execute_and_wait(
            command=["claude", "chat"],
            input_text="test prompt",
            timeout_seconds=1,
        )

        assert result.success is False
        assert "timed out" in result.error.lower() if result.error else False
        assert result.exit_code == -1
        mock_process.kill.assert_called_once()


@pytest.mark.asyncio
async def test_execute_binary_not_found(adapter: ClaudeCLIAdapter):
    with patch(
        "adapters.cli.claude_adapter.asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError(),
    ):
        result = await adapter.execute_and_wait(
            command=["nonexistent"],
            input_text="test prompt",
            timeout_seconds=30,
        )

        assert result.success is False
        assert "not found" in result.error.lower() if result.error else False
        assert result.exit_code == -1


@pytest.mark.asyncio
async def test_extract_tokens():
    adapter = ClaudeCLIAdapter()

    assert adapter._extract_tokens("Used 150 tokens") == 150
    assert adapter._extract_tokens("10 TOKENS USED") == 10
    assert adapter._extract_tokens("No tokens here") == 0


@pytest.mark.asyncio
async def test_extract_cost():
    adapter = ClaudeCLIAdapter()

    assert adapter._extract_cost("Cost: $2.50 USD") == 2.50
    assert adapter._extract_cost("0.15 cost") == 0.15
    assert adapter._extract_cost("No cost here") == 0.0


@pytest.mark.asyncio
async def test_execute_with_cost_and_tokens(adapter: ClaudeCLIAdapter):
    mock_process = AsyncMock()
    mock_process.returncode = 0
    output = b"Response here\n150 tokens used\nCost: $0.45 USD"
    mock_process.communicate = AsyncMock(return_value=(output, b""))

    with patch(
        "adapters.cli.claude_adapter.asyncio.create_subprocess_exec",
        return_value=mock_process,
    ):
        result = await adapter.execute_and_wait(
            command=["claude", "chat"],
            input_text="test",
            timeout_seconds=30,
        )

        assert result.success is True
        assert result.tokens_used == 150
        assert result.cost_usd == 0.45
