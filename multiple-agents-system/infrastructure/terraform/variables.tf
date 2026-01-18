# ============================================
# TERRAFORM VARIABLES
# ============================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "enterprise-agentcore"
}

# ============================================
# BEDROCK MODEL CONFIGURATION
# ============================================

variable "discovery_agent_model_id" {
  description = "Bedrock model ID for Discovery Agent"
  type        = string
  default     = "anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "planning_agent_model_id" {
  description = "Bedrock model ID for Planning Agent"
  type        = string
  default     = "anthropic.claude-opus-4-20250514-v1:0"
}

variable "execution_agent_model_id" {
  description = "Bedrock model ID for Execution Agent"
  type        = string
  default     = "anthropic.claude-opus-4-20250514-v1:0"
}

variable "cicd_agent_model_id" {
  description = "Bedrock model ID for CI/CD Agent"
  type        = string
  default     = "anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "sentry_agent_model_id" {
  description = "Bedrock model ID for Sentry Agent"
  type        = string
  default     = "anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "slack_agent_model_id" {
  description = "Bedrock model ID for Slack Agent"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

# ============================================
# GITHUB CONFIGURATION
# ============================================

variable "github_org" {
  description = "GitHub organization name"
  type        = string
}

variable "github_mcp_server_url" {
  description = "URL of the GitHub MCP server"
  type        = string
}

# ============================================
# JIRA CONFIGURATION
# ============================================

variable "jira_base_url" {
  description = "Jira base URL (e.g., https://company.atlassian.net)"
  type        = string
}

variable "jira_project_key" {
  description = "Default Jira project key"
  type        = string
  default     = "PROJ"
}

# ============================================
# SENTRY CONFIGURATION
# ============================================

variable "sentry_org" {
  description = "Sentry organization slug"
  type        = string
}

variable "sentry_mcp_server_url" {
  description = "URL of the Sentry MCP server"
  type        = string
  default     = "https://sentry.io/api/0/mcp"
}

# ============================================
# KNOWLEDGE BASE
# ============================================

variable "knowledge_base_id" {
  description = "Existing Knowledge Base ID (leave empty to create new)"
  type        = string
  default     = ""
}

# ============================================
# LOCALS
# ============================================

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
