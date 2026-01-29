#!/bin/bash
set -e

echo "🔐 OAuth Setup Script"
echo "===================="
echo ""

function setup_github() {
    echo "📦 Setting up GitHub OAuth App..."
    echo ""
    echo "1. Go to: https://github.com/settings/developers"
    echo "2. Click 'New OAuth App'"
    echo "3. Fill in the following:"
    echo "   - Application name: Agent Bot"
    echo "   - Homepage URL: http://localhost:8080"
    echo "   - Authorization callback URL: http://localhost:8080/auth/github/callback"
    echo ""
    read -p "Enter Client ID: " github_client_id
    read -sp "Enter Client Secret: " github_client_secret
    echo ""

    echo "GITHUB_CLIENT_ID=${github_client_id}" >> .env
    echo "GITHUB_CLIENT_SECRET=${github_client_secret}" >> .env
    echo "✓ GitHub OAuth configured"
    echo ""
}

function setup_slack() {
    echo "💬 Setting up Slack App..."
    echo ""
    echo "1. Go to: https://api.slack.com/apps"
    echo "2. Click 'Create New App' > 'From scratch'"
    echo "3. Name it 'Agent Bot' and select your workspace"
    echo "4. Navigate to 'OAuth & Permissions'"
    echo "5. Add redirect URL: http://localhost:8080/auth/slack/callback"
    echo "6. Add Bot Token Scopes: chat:write, channels:read, groups:read"
    echo ""
    read -p "Enter Client ID: " slack_client_id
    read -sp "Enter Client Secret: " slack_client_secret
    echo ""
    read -sp "Enter Signing Secret: " slack_signing_secret
    echo ""

    echo "SLACK_CLIENT_ID=${slack_client_id}" >> .env
    echo "SLACK_CLIENT_SECRET=${slack_client_secret}" >> .env
    echo "SLACK_SIGNING_SECRET=${slack_signing_secret}" >> .env
    echo "✓ Slack App configured"
    echo ""
}

function setup_jira() {
    echo "🎫 Setting up Jira OAuth..."
    echo ""
    echo "1. Go to: https://developer.atlassian.com/console/myapps/"
    echo "2. Click 'Create' > 'OAuth 2.0 integration'"
    echo "3. Name it 'Agent Bot'"
    echo "4. Add callback URL: http://localhost:8080/auth/jira/callback"
    echo "5. Add permissions: read:jira-work, write:jira-work"
    echo ""
    read -p "Enter Client ID: " jira_client_id
    read -sp "Enter Client Secret: " jira_client_secret
    echo ""
    read -p "Enter Base URL (e.g., https://yourcompany.atlassian.net): " jira_base_url

    echo "JIRA_CLIENT_ID=${jira_client_id}" >> .env
    echo "JIRA_CLIENT_SECRET=${jira_client_secret}" >> .env
    echo "JIRA_BASE_URL=${jira_base_url}" >> .env
    echo "✓ Jira OAuth configured"
    echo ""
}

function setup_sentry() {
    echo "🐛 Setting up Sentry Integration..."
    echo ""
    echo "1. Go to: https://sentry.io/settings/account/api/auth-tokens/"
    echo "2. Click 'Create New Token'"
    echo "3. Select scopes: project:read, project:write"
    echo ""
    read -sp "Enter Auth Token: " sentry_auth_token
    echo ""
    read -p "Enter Organization Slug: " sentry_org

    echo "SENTRY_AUTH_TOKEN=${sentry_auth_token}" >> .env
    echo "SENTRY_ORGANIZATION=${sentry_org}" >> .env
    echo "✓ Sentry configured"
    echo ""
}

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
fi

echo "Select services to configure:"
echo "1) GitHub"
echo "2) Slack"
echo "3) Jira"
echo "4) Sentry"
echo "5) All"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1) setup_github ;;
    2) setup_slack ;;
    3) setup_jira ;;
    4) setup_sentry ;;
    5)
        setup_github
        setup_slack
        setup_jira
        setup_sentry
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ OAuth setup complete!"
echo "Your credentials have been saved to .env"
echo ""
echo "⚠️  IMPORTANT: Never commit .env to version control!"
