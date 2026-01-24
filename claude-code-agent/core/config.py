"""Application configuration."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars without validation errors
    )

    # Machine Identity
    machine_id: str = "claude-agent-001"

    # Task Management
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 3600

    # Paths
    data_dir: Path = Path("/data")
    app_dir: Path = Path("/app")

    # Database
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "sqlite+aiosqlite:////data/db/machine.db"

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]

    # Webhook Security
    github_webhook_secret: str | None = None
    jira_webhook_secret: str | None = None
    
    # Jira API Configuration
    jira_url: str | None = None  # e.g., "https://yourcompany.atlassian.net"
    jira_email: str | None = None  # Email for Jira API authentication
    jira_api_token: str | None = None
    jira_ai_agent_name: str = "AI Agent"  # Name of the AI agent in Jira (for assignee matching)
    
    # Webhook Public Domain (for displaying URLs)
    webhook_public_domain: str | None = None  # e.g., "abc123.ngrok.io" or "webhooks.yourdomain.com"

    # Storage Backend (for cloud deployment)
    storage_backend: str = "local"  # "local", "s3", or "postgresql"
    s3_bucket: str | None = None
    s3_prefix: str = "claude-agent"

    # Claude CLI Configuration
    default_allowed_tools: str = "Read,Edit,Bash,Glob,Grep,Write"  # Pre-approved tools
    
    # Claude Code Tasks Integration
    sync_to_claude_tasks: bool = False  # Sync orchestration tasks to Claude Code Tasks directory
    claude_tasks_directory: Optional[Path] = None  # Default: ~/.claude/tasks
    
    # Model Configuration by Agent Type
    claude_model_planning: str = "claude-opus-4-5-20251101"      # Complex tasks, thinking, planning
    claude_model_brain: str = "claude-opus-4-5-20251101"         # Brain agent for orchestration
    claude_model_executor: str = "claude-sonnet-4-5-20250929"    # Execution, faster tasks
    claude_default_model: str = "claude-sonnet-4-5-20250929"     # Default fallback model

    @property
    def agents_dir(self) -> Path:
        """Directory containing BUILT-IN sub-agents (in .claude/agents/)."""
        return self.app_dir / ".claude" / "agents"

    @property
    def user_agents_dir(self) -> Path:
        """Directory for USER-UPLOADED agents (persisted in /data volume)."""
        return self.data_dir / "config" / "agents"

    @property
    def skills_dir(self) -> Path:
        """Directory containing BUILT-IN skills (in .claude/skills/)."""
        return self.app_dir / ".claude" / "skills"

    @property
    def user_skills_dir(self) -> Path:
        """Directory for USER-UPLOADED skills (persisted in /data volume)."""
        return self.data_dir / "config" / "skills"

    @property
    def credentials_path(self) -> Path:
        """Path to credentials file (persisted in /data volume)."""
        return self.data_dir / "credentials" / "claude.json"

    @property
    def registry_dir(self) -> Path:
        """Directory containing registry files (persisted in /data volume)."""
        return self.data_dir / "registry"
    
    def get_model_for_agent(self, agent_type: str) -> str:
        """
        Get the appropriate Claude model for a given agent type.
        
        Args:
            agent_type: Agent type (planning, executor, brain)
            
        Returns:
            Model name (e.g., "opus-4", "sonnet-4")
        """
        agent_type_lower = agent_type.lower()
        
        if agent_type_lower == "planning":
            return self.claude_model_planning
        elif agent_type_lower == "executor":
            return self.claude_model_executor
        elif agent_type_lower == "brain":
            return self.claude_model_brain
        else:
            return self.claude_default_model


# Global settings instance
settings = Settings()
