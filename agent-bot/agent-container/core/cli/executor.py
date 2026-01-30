"""Main CLI executor factory."""

import os
from typing import Literal
from .base import CLIExecutor
from .providers.claude.executor import ClaudeExecutor
from .providers.cursor.executor import CursorExecutor


def get_executor(provider: Literal["claude-code-cli", "cursor-cli"] | None = None) -> CLIExecutor:
    """Get CLI executor based on provider."""
    if provider is None:
        provider_str = os.getenv("CLI_PROVIDER", "claude-code-cli")
        if provider_str not in ["claude-code-cli", "cursor-cli"]:
            raise ValueError(f"Invalid CLI provider: {provider_str}")
        provider = provider_str

    if provider == "claude-code-cli":
        return ClaudeExecutor()
    elif provider == "cursor-cli":
        return CursorExecutor()
    else:
        raise ValueError(f"Unknown CLI provider: {provider}")
