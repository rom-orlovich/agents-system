"""
Centralized Configuration Settings
==================================
All static parameters are loaded from environment variables.
This module provides type-safe access to all configuration values.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from functools import lru_cache


@dataclass(frozen=True)
class AWSConfig:
    """AWS Configuration"""
    region: str = os.getenv("AWS_REGION", "us-east-1")
    account_id: str = os.getenv("AWS_ACCOUNT_ID", "")
    project_name: str = os.getenv("PROJECT_NAME", "enterprise-agentcore")
    environment: str = os.getenv("ENVIRONMENT", "development")


@dataclass(frozen=True)
class AgentModelConfig:
    """Agent Model Configuration"""
    discovery_model: str = os.getenv("DISCOVERY_AGENT_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
    planning_model: str = os.getenv("PLANNING_AGENT_MODEL_ID", "anthropic.claude-opus-4-20250514-v1:0")
    execution_model: str = os.getenv("EXECUTION_AGENT_MODEL_ID", "anthropic.claude-opus-4-20250514-v1:0")
    cicd_model: str = os.getenv("CICD_AGENT_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
    sentry_model: str = os.getenv("SENTRY_AGENT_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
    slack_model: str = os.getenv("SLACK_AGENT_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")


@dataclass(frozen=True)
class AgentRuntimeConfig:
    """Agent Runtime Configuration"""
    # Discovery Agent
    discovery_memory_mb: int = int(os.getenv("DISCOVERY_AGENT_MEMORY_MB", "2048"))
    discovery_vcpu: float = float(os.getenv("DISCOVERY_AGENT_VCPU", "1.0"))
    discovery_timeout: int = int(os.getenv("DISCOVERY_AGENT_TIMEOUT_SECONDS", "1800"))
    
    # Planning Agent
    planning_memory_mb: int = int(os.getenv("PLANNING_AGENT_MEMORY_MB", "4096"))
    planning_vcpu: float = float(os.getenv("PLANNING_AGENT_VCPU", "2.0"))
    planning_timeout: int = int(os.getenv("PLANNING_AGENT_TIMEOUT_SECONDS", "3600"))
    
    # Execution Agent
    execution_memory_mb: int = int(os.getenv("EXECUTION_AGENT_MEMORY_MB", "4096"))
    execution_vcpu: float = float(os.getenv("EXECUTION_AGENT_VCPU", "2.0"))
    execution_timeout: int = int(os.getenv("EXECUTION_AGENT_TIMEOUT_SECONDS", "7200"))
    
    # CI/CD Agent
    cicd_memory_mb: int = int(os.getenv("CICD_AGENT_MEMORY_MB", "2048"))
    cicd_vcpu: float = float(os.getenv("CICD_AGENT_VCPU", "1.0"))
    cicd_timeout: int = int(os.getenv("CICD_AGENT_TIMEOUT_SECONDS", "1800"))
    
    # Sentry Agent
    sentry_memory_mb: int = int(os.getenv("SENTRY_AGENT_MEMORY_MB", "1024"))
    sentry_vcpu: float = float(os.getenv("SENTRY_AGENT_VCPU", "0.5"))
    sentry_timeout: int = int(os.getenv("SENTRY_AGENT_TIMEOUT_SECONDS", "900"))
    
    # Slack Agent
    slack_memory_mb: int = int(os.getenv("SLACK_AGENT_MEMORY_MB", "512"))
    slack_vcpu: float = float(os.getenv("SLACK_AGENT_VCPU", "0.25"))
    slack_timeout: int = int(os.getenv("SLACK_AGENT_TIMEOUT_SECONDS", "300"))


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub Configuration"""
    org: str = os.getenv("GITHUB_ORG", "")
    token: str = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    mcp_server_url: str = os.getenv("GITHUB_MCP_SERVER_URL", "")
    oauth_client_id: str = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
    oauth_client_secret: str = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")


@dataclass(frozen=True)
class JiraConfig:
    """Jira/Atlassian Configuration"""
    base_url: str = os.getenv("JIRA_BASE_URL", "")
    project_key: str = os.getenv("JIRA_PROJECT_KEY", "PROJ")
    oauth_client_id: str = os.getenv("JIRA_OAUTH_CLIENT_ID", "")
    oauth_client_secret: str = os.getenv("JIRA_OAUTH_CLIENT_SECRET", "")
    webhook_secret: str = os.getenv("JIRA_WEBHOOK_SECRET", "")
    ai_label: str = os.getenv("JIRA_AI_LABEL", "AI")
    auto_label: str = os.getenv("JIRA_AUTO_LABEL", "sentry-auto")
    error_label: str = os.getenv("JIRA_ERROR_LABEL", "error")


@dataclass(frozen=True)
class SentryConfig:
    """Sentry Configuration"""
    org: str = os.getenv("SENTRY_ORG", "")
    auth_token: str = os.getenv("SENTRY_AUTH_TOKEN", "")
    webhook_secret: str = os.getenv("SENTRY_WEBHOOK_SECRET", "")
    mcp_server_url: str = os.getenv("SENTRY_MCP_SERVER_URL", "")
    threshold_fatal: int = int(os.getenv("SENTRY_THRESHOLD_FATAL", "1"))
    threshold_error: int = int(os.getenv("SENTRY_THRESHOLD_ERROR", "10"))
    threshold_warning: int = int(os.getenv("SENTRY_THRESHOLD_WARNING", "50"))
    threshold_info: int = int(os.getenv("SENTRY_THRESHOLD_INFO", "100"))
    
    @property
    def thresholds(self) -> Dict[str, int]:
        return {
            "fatal": self.threshold_fatal,
            "error": self.threshold_error,
            "warning": self.threshold_warning,
            "info": self.threshold_info
        }


@dataclass(frozen=True)
class SlackConfig:
    """Slack Configuration"""
    bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")
    app_token: str = os.getenv("SLACK_APP_TOKEN", "")
    channel_agents: str = os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agents")
    channel_errors: str = os.getenv("SLACK_CHANNEL_ERRORS", "#errors")
    channel_alerts: str = os.getenv("SLACK_CHANNEL_ALERTS", "#alerts")


@dataclass(frozen=True)
class DynamoDBConfig:
    """DynamoDB Configuration"""
    tasks_table: str = os.getenv("DYNAMODB_TASKS_TABLE", "enterprise-agentcore-tasks")
    error_tracking_table: str = os.getenv("DYNAMODB_ERROR_TRACKING_TABLE", "enterprise-agentcore-error-tracking")
    sessions_table: str = os.getenv("DYNAMODB_SESSIONS_TABLE", "enterprise-agentcore-sessions")


@dataclass(frozen=True)
class S3Config:
    """S3 Configuration"""
    artifacts_bucket: str = os.getenv("S3_ARTIFACTS_BUCKET", "enterprise-agentcore-artifacts")
    plans_prefix: str = os.getenv("S3_PLANS_PREFIX", "plans/")
    code_cache_prefix: str = os.getenv("S3_CODE_CACHE_PREFIX", "code-cache/")
    logs_prefix: str = os.getenv("S3_LOGS_PREFIX", "logs/")


@dataclass(frozen=True)
class APIGatewayConfig:
    """API Gateway Configuration"""
    stage: str = os.getenv("API_GATEWAY_STAGE", "prod")
    rate_limit: int = int(os.getenv("API_GATEWAY_RATE_LIMIT", "100"))
    burst_limit: int = int(os.getenv("API_GATEWAY_BURST_LIMIT", "200"))
    custom_domain: str = os.getenv("API_GATEWAY_CUSTOM_DOMAIN", "")


@dataclass(frozen=True)
class StepFunctionsConfig:
    """Step Functions Configuration"""
    max_concurrency: int = int(os.getenv("SFN_MAX_CONCURRENCY", "10"))
    approval_timeout: int = int(os.getenv("SFN_APPROVAL_TIMEOUT_SECONDS", "86400"))


@dataclass(frozen=True)
class CodeInterpreterConfig:
    """Code Interpreter Configuration"""
    memory_mb: int = int(os.getenv("CODE_INTERPRETER_MEMORY_MB", "2048"))
    timeout_seconds: int = int(os.getenv("CODE_INTERPRETER_TIMEOUT_SECONDS", "300"))
    filesystem_size_mb: int = int(os.getenv("CODE_INTERPRETER_FILESYSTEM_SIZE_MB", "5120"))
    network_access: bool = os.getenv("CODE_INTERPRETER_NETWORK_ACCESS", "false").lower() == "true"
    
    @property
    def python_packages(self) -> List[str]:
        packages = os.getenv("CODE_INTERPRETER_PYTHON_PACKAGES", "pytest,requests,boto3,pandas,numpy")
        return [p.strip() for p in packages.split(",") if p.strip()]
    
    @property
    def npm_packages(self) -> List[str]:
        packages = os.getenv("CODE_INTERPRETER_NPM_PACKAGES", "jest,@testing-library/react,eslint,prettier")
        return [p.strip() for p in packages.split(",") if p.strip()]


@dataclass(frozen=True)
class MemoryConfig:
    """AgentCore Memory Configuration"""
    short_term_max_events: int = int(os.getenv("MEMORY_SHORT_TERM_MAX_EVENTS", "100"))
    short_term_ttl_seconds: int = int(os.getenv("MEMORY_SHORT_TERM_TTL_SECONDS", "3600"))
    embedding_model_id: str = os.getenv("MEMORY_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    vector_dimensions: int = int(os.getenv("MEMORY_VECTOR_DIMENSIONS", "1024"))


@dataclass(frozen=True)
class LoggingConfig:
    """Logging & Monitoring Configuration"""
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_xray: bool = os.getenv("ENABLE_XRAY_TRACING", "true").lower() == "true"
    enable_cloudwatch_insights: bool = os.getenv("ENABLE_CLOUDWATCH_INSIGHTS", "true").lower() == "true"
    cloudwatch_namespace: str = os.getenv("CLOUDWATCH_NAMESPACE", "AgentSystem")


@dataclass(frozen=True)
class SecurityConfig:
    """Security Configuration"""
    enable_waf: bool = os.getenv("ENABLE_WAF", "true").lower() == "true"
    waf_rate_limit: int = int(os.getenv("WAF_RATE_LIMIT", "100"))
    secrets_prefix: str = os.getenv("SECRETS_PREFIX", "enterprise-agentcore/")


@dataclass(frozen=True)
class RetryConfig:
    """Retry Configuration"""
    max_task_attempts: int = int(os.getenv("MAX_TASK_RETRY_ATTEMPTS", "3"))
    max_ci_fix_attempts: int = int(os.getenv("MAX_CI_FIX_ATTEMPTS", "3"))
    backoff_base_seconds: int = int(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "5"))


@dataclass(frozen=True)
class ConventionsConfig:
    """Organization Conventions Configuration"""
    branch_naming_pattern: str = os.getenv("BRANCH_NAMING_PATTERN", "feature/{ticket_id}-{slug}")
    commit_prefix_feature: str = os.getenv("COMMIT_PREFIX_FEATURE", "feat:")
    commit_prefix_fix: str = os.getenv("COMMIT_PREFIX_FIX", "fix:")
    commit_prefix_chore: str = os.getenv("COMMIT_PREFIX_CHORE", "chore:")
    pr_template_path: str = os.getenv("PR_TEMPLATE_PATH", ".github/PULL_REQUEST_TEMPLATE.md")
    
    @property
    def test_frameworks(self) -> Dict[str, str]:
        return {
            "python": os.getenv("TEST_FRAMEWORK_PYTHON", "pytest"),
            "javascript": os.getenv("TEST_FRAMEWORK_JAVASCRIPT", "jest"),
            "typescript": os.getenv("TEST_FRAMEWORK_TYPESCRIPT", "jest"),
            "go": os.getenv("TEST_FRAMEWORK_GO", "go test"),
        }
    
    def format_branch_name(self, ticket_id: str, slug: str) -> str:
        return self.branch_naming_pattern.format(
            ticket_id=ticket_id.lower(),
            slug=slug.lower().replace(" ", "-")[:50]
        )


@dataclass(frozen=True)
class CostConfig:
    """Cost Management Configuration"""
    monthly_budget_alert: int = int(os.getenv("MONTHLY_BUDGET_ALERT_USD", "500"))
    anomaly_threshold_percent: int = int(os.getenv("COST_ANOMALY_THRESHOLD_PERCENT", "50"))


@dataclass(frozen=True)
class Settings:
    """Main Settings Container - Singleton"""
    aws: AWSConfig = field(default_factory=AWSConfig)
    models: AgentModelConfig = field(default_factory=AgentModelConfig)
    runtimes: AgentRuntimeConfig = field(default_factory=AgentRuntimeConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    jira: JiraConfig = field(default_factory=JiraConfig)
    sentry: SentryConfig = field(default_factory=SentryConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    dynamodb: DynamoDBConfig = field(default_factory=DynamoDBConfig)
    s3: S3Config = field(default_factory=S3Config)
    api_gateway: APIGatewayConfig = field(default_factory=APIGatewayConfig)
    step_functions: StepFunctionsConfig = field(default_factory=StepFunctionsConfig)
    code_interpreter: CodeInterpreterConfig = field(default_factory=CodeInterpreterConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    conventions: ConventionsConfig = field(default_factory=ConventionsConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    
    @property
    def is_production(self) -> bool:
        return self.aws.environment.lower() in ["production", "prod"]
    
    @property
    def log_level(self) -> str:
        if self.is_production:
            return "INFO"
        return self.logging.log_level


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get singleton Settings instance"""
    return Settings()


# Convenience exports
settings = get_settings()
