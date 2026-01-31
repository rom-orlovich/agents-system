from dataclasses import dataclass


@dataclass(frozen=True)
class ClaudeConfig:
    command: str = "claude"
    supports_mcp: bool = True
    supports_git: bool = True
    config_path: str = ".claude/"
    init_command: str = "claude init"
    mcp_config_file: str = "mcp.json"
    output_format: str = "stream-json"


CLAUDE_CONFIG = ClaudeConfig()
