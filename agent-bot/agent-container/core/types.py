from typing import Protocol

JsonValue = str | int | bool | float | None
JsonDict = dict[str, JsonValue | dict | list]


class MCPClientProtocol(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, JsonValue]) -> bool: ...
