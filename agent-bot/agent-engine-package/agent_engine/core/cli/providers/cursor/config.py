from dataclasses import dataclass


@dataclass(frozen=True)
class CursorConfig:
    command: str = "cursor"
    subcommand: str = "agent"
    supports_mcp: bool = True
    supports_git: bool = True
    config_path: str = ".cursor/"
    init_command: str = "cursor init"
    mcp_config_file: str = "mcp.json"
    mcp_approvals_file: str = "mcp-approvals.json"
    output_format: str = "json-stream"
    print_mode: bool = True
    headless: bool = True


CURSOR_CONFIG = CursorConfig()
