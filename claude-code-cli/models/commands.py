"""Command system models."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from types.enums import CommandType, Platform


@dataclass
class CommandParameter:
    """A parameter for a command."""
    name: str
    param_type: str
    required: bool
    description: str
    default: Optional[Any] = None


@dataclass
class CommandDefinition:
    """Definition of a bot command."""
    name: str
    aliases: List[str]
    description: str
    usage: str
    examples: List[str]
    parameters: List[CommandParameter]
    handler: str
    platforms: List[Platform]
    response_template: Optional[str] = None


@dataclass
class ParsedCommand:
    """A parsed command from user input."""
    command_type: CommandType
    command_name: str
    definition: Optional[CommandDefinition]
    args: List[str]
    raw_text: str
    platform: Platform
    context: Dict[str, Any]


@dataclass
class CommandResult:
    """Result of executing a command."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    should_reply: bool = True
    reaction: Optional[str] = None
