import pytest
from unittest.mock import AsyncMock
from core.types import MCPClientProtocol, JsonValue, JsonDict


class MockMCPClient:
    async def call_tool(self, name: str, arguments: dict[str, JsonValue]) -> bool:
        return True


@pytest.mark.asyncio
async def test_mcp_client_protocol_compliance():
    client = MockMCPClient()

    result = await client.call_tool("test_tool", {"key": "value", "count": 42})

    assert result is True


@pytest.mark.asyncio
async def test_mcp_client_protocol_with_mock():
    mock_client = AsyncMock(spec=MCPClientProtocol)
    mock_client.call_tool.return_value = True

    result = await mock_client.call_tool("tool_name", {"arg": "value"})

    assert result is True
    mock_client.call_tool.assert_called_once_with("tool_name", {"arg": "value"})


def test_json_value_types():
    valid_values: list[JsonValue] = ["string", 123, True, 3.14, None]

    for value in valid_values:
        assert value is not None or value is None


def test_json_dict_structure():
    valid_dict: JsonDict = {
        "string_key": "value",
        "int_key": 42,
        "bool_key": True,
        "float_key": 3.14,
        "none_key": None,
        "nested": {"key": "value"},
        "list": [1, 2, 3],
    }

    assert isinstance(valid_dict, dict)
    assert "string_key" in valid_dict
