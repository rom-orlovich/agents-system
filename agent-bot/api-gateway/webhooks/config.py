from dataclasses import dataclass
from enum import Enum


class ModelType(str, Enum):
    OPUS = "claude-opus-4-5-20251101"
    SONNET = "claude-sonnet-4-5-20250929"


class AgentType(str, Enum):
    PLANNING = "planning"
    CODING = "coding"
    REVIEW = "review"
    BUG_FIX = "bug-fix"
    ANALYZE = "analyze"


@dataclass(frozen=True)
class CommandConfig:
    pattern: str
    agent_name: str
    model: ModelType


@dataclass(frozen=True)
class WebhookConfig:
    commands: list[CommandConfig]

    def match_command(self, message: str) -> CommandConfig | None:
        message_lower = message.lower()
        for command in self.commands:
            if command.pattern.lower() in message_lower:
                return command
        return None


def create_default_github_config() -> WebhookConfig:
    return WebhookConfig(
        commands=[
            CommandConfig(
                pattern="@agent review",
                agent_name=AgentType.REVIEW.value,
                model=ModelType.OPUS,
            ),
            CommandConfig(
                pattern="@agent fix",
                agent_name=AgentType.BUG_FIX.value,
                model=ModelType.SONNET,
            ),
            CommandConfig(
                pattern="@agent analyze",
                agent_name=AgentType.ANALYZE.value,
                model=ModelType.OPUS,
            ),
            CommandConfig(
                pattern="@agent",
                agent_name=AgentType.PLANNING.value,
                model=ModelType.OPUS,
            ),
        ]
    )


def create_default_slack_config() -> WebhookConfig:
    return WebhookConfig(
        commands=[
            CommandConfig(
                pattern="@agent review",
                agent_name=AgentType.REVIEW.value,
                model=ModelType.OPUS,
            ),
            CommandConfig(
                pattern="@agent fix",
                agent_name=AgentType.BUG_FIX.value,
                model=ModelType.SONNET,
            ),
            CommandConfig(
                pattern="@agent analyze",
                agent_name=AgentType.ANALYZE.value,
                model=ModelType.OPUS,
            ),
            CommandConfig(
                pattern="@agent code",
                agent_name=AgentType.CODING.value,
                model=ModelType.SONNET,
            ),
            CommandConfig(
                pattern="@agent",
                agent_name=AgentType.PLANNING.value,
                model=ModelType.OPUS,
            ),
        ]
    )


def create_default_jira_config() -> WebhookConfig:
    return WebhookConfig(
        commands=[
            CommandConfig(
                pattern="@agent review",
                agent_name=AgentType.REVIEW.value,
                model=ModelType.OPUS,
            ),
            CommandConfig(
                pattern="@agent fix",
                agent_name=AgentType.BUG_FIX.value,
                model=ModelType.SONNET,
            ),
            CommandConfig(
                pattern="@agent analyze",
                agent_name=AgentType.ANALYZE.value,
                model=ModelType.OPUS,
            ),
            CommandConfig(
                pattern="@agent",
                agent_name=AgentType.PLANNING.value,
                model=ModelType.OPUS,
            ),
        ]
    )


def create_default_sentry_config() -> WebhookConfig:
    return WebhookConfig(
        commands=[
            CommandConfig(
                pattern="",
                agent_name=AgentType.BUG_FIX.value,
                model=ModelType.SONNET,
            ),
        ]
    )
