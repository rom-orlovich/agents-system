import re
from pathlib import Path
from typing import List, Optional, Set
from pydantic import BaseModel, Field, field_validator, model_validator


class CommandPrefix(BaseModel):
    prefix: str = Field(..., min_length=1, description="Command prefix like @agent or /claude")
    description: str = Field(default="", description="Human-readable description")
    enabled: bool = Field(default=True, description="Whether this prefix is active")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        if not v.startswith(("@", "/")):
            raise ValueError("Prefix must start with @ or /")
        return v.lower()


class CommandDefinition(BaseModel):
    name: str = Field(..., min_length=1, description="Primary command name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names for the command")
    description: str = Field(default="", description="What this command does")
    target_agent: str = Field(default="brain", description="Agent that handles this command")
    requires_approval: bool = Field(default=False, description="Whether execution requires approval")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9-]*$", v.lower()):
            raise ValueError("Command name must be alphanumeric with hyphens")
        return v.lower()

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, v: List[str]) -> List[str]:
        return [alias.lower() for alias in v]

    def matches(self, word: str) -> bool:
        word_lower = word.lower()
        return word_lower == self.name or word_lower in self.aliases

    @property
    def all_names(self) -> List[str]:
        return [self.name] + self.aliases


class BotPatterns(BaseModel):
    usernames: List[str] = Field(default_factory=list, description="Bot usernames to ignore")
    type_patterns: List[str] = Field(default_factory=list, description="Type patterns indicating bots")

    @field_validator("usernames")
    @classmethod
    def normalize_usernames(cls, v: List[str]) -> List[str]:
        return [u.lower() for u in v]


class CommandDefaults(BaseModel):
    default_command: str = Field(default="analyze", description="Default when no command specified")
    case_sensitive: bool = Field(default=False, description="Whether matching is case-sensitive")


class CommandsConfig(BaseModel):
    prefixes: List[CommandPrefix] = Field(default_factory=list)
    commands: List[CommandDefinition] = Field(default_factory=list)
    bot_patterns: BotPatterns = Field(default_factory=BotPatterns)
    defaults: CommandDefaults = Field(default_factory=CommandDefaults)

    _command_pattern: Optional[re.Pattern] = None
    _command_lookup: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def build_lookup_tables(self) -> "CommandsConfig":
        object.__setattr__(self, "_command_lookup", self._build_command_lookup())
        object.__setattr__(self, "_command_pattern", self._build_pattern())
        return self

    def _build_command_lookup(self) -> dict:
        lookup = {}
        for cmd in self.commands:
            lookup[cmd.name] = cmd
            for alias in cmd.aliases:
                lookup[alias] = cmd
        return lookup

    def _build_pattern(self) -> re.Pattern:
        enabled_prefixes = [p.prefix for p in self.prefixes if p.enabled]
        if not enabled_prefixes:
            enabled_prefixes = ["@agent"]

        escaped_prefixes = [re.escape(p) for p in enabled_prefixes]
        prefix_group = "|".join(escaped_prefixes)

        pattern = rf"(?:^|\s)({prefix_group})\s+(\w+)(?:\s+(.*))?"
        flags = re.DOTALL if not self.defaults.case_sensitive else re.DOTALL
        if not self.defaults.case_sensitive:
            flags |= re.IGNORECASE
        return re.compile(pattern, flags)

    @property
    def enabled_prefixes(self) -> List[str]:
        return [p.prefix for p in self.prefixes if p.enabled]

    @property
    def valid_command_names(self) -> Set[str]:
        names = set()
        for cmd in self.commands:
            names.add(cmd.name)
            names.update(cmd.aliases)
        return names

    @property
    def bot_usernames(self) -> List[str]:
        return self.bot_patterns.usernames

    @property
    def command_pattern(self) -> re.Pattern:
        if self._command_pattern is None:
            object.__setattr__(self, "_command_pattern", self._build_pattern())
        return self._command_pattern

    def get_command(self, name: str) -> Optional[CommandDefinition]:
        if self._command_lookup is None:
            object.__setattr__(self, "_command_lookup", self._build_command_lookup())
        return self._command_lookup.get(name.lower())

    def is_valid_command(self, name: str) -> bool:
        return name.lower() in self.valid_command_names

    def has_prefix(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(prefix in text_lower for prefix in self.enabled_prefixes)


def load_commands_config(config_path: Optional[Path] = None) -> CommandsConfig:
    import yaml

    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "commands.yaml"

    if not config_path.exists():
        return _get_default_config()

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return CommandsConfig(**data)


def _get_default_config() -> CommandsConfig:
    return CommandsConfig(
        prefixes=[
            CommandPrefix(prefix="@agent", description="Primary prefix", enabled=True),
            CommandPrefix(prefix="/agent", description="Slash variant", enabled=True),
            CommandPrefix(prefix="@claude", description="Claude prefix", enabled=True),
            CommandPrefix(prefix="/claude", description="Claude slash variant", enabled=True),
        ],
        commands=[
            CommandDefinition(name="analyze", aliases=["analysis"], target_agent="planning"),
            CommandDefinition(name="plan", aliases=["plan-fix"], target_agent="planning"),
            CommandDefinition(name="fix", aliases=["implement"], target_agent="executor", requires_approval=True),
            CommandDefinition(name="review", aliases=["code-review"], target_agent="planning"),
            CommandDefinition(name="approve", aliases=["lgtm"], target_agent="executor"),
            CommandDefinition(name="reject", aliases=["changes-requested"], target_agent="planning"),
            CommandDefinition(name="improve", aliases=["enhance"], target_agent="executor", requires_approval=True),
            CommandDefinition(name="help", aliases=["commands"], target_agent="brain"),
            CommandDefinition(name="discover", aliases=["code", "explore"], target_agent="planning"),
            CommandDefinition(name="jira", aliases=["ticket"], target_agent="slack-inquiry"),
        ],
        bot_patterns=BotPatterns(
            usernames=["github-actions[bot]", "claude-agent", "ai-agent", "dependabot[bot]"],
            type_patterns=["bot", "Bot", "[bot]"],
        ),
        defaults=CommandDefaults(default_command="analyze", case_sensitive=False),
    )


_cached_config: Optional[CommandsConfig] = None


def get_commands_config() -> CommandsConfig:
    global _cached_config
    if _cached_config is None:
        _cached_config = load_commands_config()
    return _cached_config


def reload_commands_config() -> CommandsConfig:
    global _cached_config
    _cached_config = load_commands_config()
    return _cached_config
