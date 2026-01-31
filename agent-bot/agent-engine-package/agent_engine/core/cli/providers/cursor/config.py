from dataclasses import dataclass


@dataclass(frozen=True)
class CursorConfig:
    command: str = "cursor"
    supports_mcp: bool = True
    supports_git: bool = True
    config_path: str = ".cursor/"
    init_command: str = "cursor init"
    mcp_config_file: str = "mcp.json"
    output_format: str = "json-stream"


CURSOR_CONFIG = CursorConfig()
