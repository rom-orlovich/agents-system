# ============================================
# SECRETS MANAGER
# ============================================

resource "aws_secretsmanager_secret" "github_token" {
  name        = "${var.project_name}/github-token"
  description = "GitHub Personal Access Token"
  
  tags = {
    Name = "${var.project_name}-github-token"
  }
}

resource "aws_secretsmanager_secret" "github_webhook_secret" {
  name        = "${var.project_name}/github-webhook-secret"
  description = "GitHub Webhook Secret"
  
  tags = {
    Name = "${var.project_name}-github-webhook-secret"
  }
}

resource "aws_secretsmanager_secret" "github_oauth_app" {
  name        = "${var.project_name}/github-oauth-app"
  description = "GitHub OAuth App Credentials"
  
  tags = {
    Name = "${var.project_name}-github-oauth-app"
  }
}

resource "aws_secretsmanager_secret" "jira_oauth_credentials" {
  name        = "${var.project_name}/jira-oauth-credentials"
  description = "Jira OAuth Credentials"
  
  tags = {
    Name = "${var.project_name}-jira-oauth-credentials"
  }
}

resource "aws_secretsmanager_secret" "sentry_token" {
  name        = "${var.project_name}/sentry-token"
  description = "Sentry Auth Token"
  
  tags = {
    Name = "${var.project_name}-sentry-token"
  }
}

resource "aws_secretsmanager_secret" "slack_credentials" {
  name        = "${var.project_name}/slack-credentials"
  description = "Slack Bot Token and Signing Secret"
  
  tags = {
    Name = "${var.project_name}-slack-credentials"
  }
}
