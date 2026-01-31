from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class CLIProviderType(str, Enum):
    CLAUDE = "claude"
    CURSOR = "cursor"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    machine_id: str = "agent-engine-001"
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 3600

    cli_provider: CLIProviderType = CLIProviderType.CLAUDE

    data_dir: Path = Path("/data")
    app_dir: Path = Path("/app")

    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+asyncpg://agent:agent@postgres:5432/agent_system"

    log_level: str = "INFO"
    log_json: bool = True
    debug_save_task_logs: bool = False

    task_logs_enabled: bool = True
    task_logs_dir: Path = Path(".log/tasks")

    api_host: str = "0.0.0.0"
    api_port: int = 8080

    cors_origins: list[str] = ["*"]

    github_webhook_secret: str | None = None
    jira_webhook_secret: str | None = None
    slack_webhook_secret: str | None = None

    github_token: str | None = None
    slack_bot_token: str | None = None

    jira_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_ai_agent_name: str = "AI Agent"

    claude_model_planning: str = "claude-opus-4-5-20251101"
    claude_model_brain: str = "claude-opus-4-5-20251101"
    claude_model_executor: str = "claude-sonnet-4-5-20250929"
    claude_default_model: str = "claude-sonnet-4-5-20250929"

    default_allowed_tools: str = "Read,Edit,Bash,Glob,Grep,Write"

    webhook_agent_prefix: str = "@agent"
    webhook_bot_usernames: str = "github-actions[bot],claude-agent,ai-agent,dependabot[bot]"
    webhook_valid_commands: str = "analyze,plan,fix,review,approve,reject,improve,help"

    max_comment_body_size: int = 10000
    max_file_content_size: int = 50000
    max_prompt_size: int = 200000

    @property
    def agents_dir(self) -> Path:
        return self.app_dir / "agents"

    @property
    def skills_dir(self) -> Path:
        return self.app_dir / "skills"

    @property
    def memory_dir(self) -> Path:
        return self.app_dir / "memory"

    @property
    def bot_usernames_list(self) -> list[str]:
        return [u.strip().lower() for u in self.webhook_bot_usernames.split(",") if u.strip()]

    @property
    def valid_commands_list(self) -> list[str]:
        return [c.strip().lower() for c in self.webhook_valid_commands.split(",") if c.strip()]

    def get_model_for_agent(self, agent_type: str) -> str:
        agent_models = {
            "planning": self.claude_model_planning,
            "executor": self.claude_model_executor,
            "brain": self.claude_model_brain,
        }
        return agent_models.get(agent_type.lower(), self.claude_default_model)


settings = Settings()
