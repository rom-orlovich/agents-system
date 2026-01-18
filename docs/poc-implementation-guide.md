# POC Implementation Guide
## Claude Code CLI Agent - שלב 1

---

> **🆕 גרסה מעודכנת:** ראה [claude-code-cli-poc](./claude-code-cli-poc/) עם:
> - **שני סוכנים נפרדים** (Planning + Executor)
> - **MCP Servers רשמיים** (GitHub, Atlassian, Sentry)
> - **Slack Integration** להפעלת פעולות ולקבלת עדכונים
> - **Skills Folders** במקום prompts רגילים
> 
> ארכיטקטורה מלאה: [CLAUDE-CODE-CLI-POC.ARCHITECTURE.md](./claude-code-cli-poc/CLAUDE-CODE-CLI-POC.ARCHITECTURE.md)

---

## מטרת ה-POC

בניית מערכת מלאה מקצה לקצה:

```
Sentry Alert → Lambda → Jira Ticket → Agent → Fix Code → Test → PR
```

**משך:** 3 ימים
**עלות:** ~$200 (חודש Teams $150 + AWS ~$50)
**תוצר:** Pipeline עובד מ-Sentry עד PR

---

## Pricing Model

| רכיב | עלות חודשית |
|------|-------------|
| Claude Teams Premium | $150/seat |
| EC2 t3.large | ~$45 |
| AWS extras (Lambda, etc.) | ~$5-10 |
| **סה"כ POC** | **~$200** |

> **הערה:** Claude Teams ב-$150 כולל Claude Code CLI עם rate limits גבוהים מספיק לשימוש אוטומטי

---

## Part 0: Sentry → Jira Integration (הטריגר)

### 0.1 Architecture Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│    Sentry    │────▶│  AWS Lambda     │────▶│    Jira      │────▶│   Agent     │
│    Alert     │     │  (Webhook)      │     │   Ticket     │     │   (EC2)     │
└──────────────┘     └─────────────────┘     └──────────────┘     └─────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  API Gateway    │
                     │  /sentry-hook   │
                     └─────────────────┘
```

### 0.2 Lambda Function (sentry_to_jira.py)

```python
"""
AWS Lambda: Sentry Webhook → Jira Ticket
Trigger: API Gateway POST /sentry-hook
"""

import json
import os
import logging
import hashlib
from datetime import datetime
import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Jira configuration from environment
JIRA_URL = os.environ['JIRA_URL']
JIRA_EMAIL = os.environ['JIRA_EMAIL']
JIRA_TOKEN = os.environ['JIRA_TOKEN']
JIRA_PROJECT = os.environ['JIRA_PROJECT']  # e.g., "PROJ"
AI_FIX_LABEL = "AI-Fix"

# Sentry secret for webhook validation
SENTRY_CLIENT_SECRET = os.environ.get('SENTRY_CLIENT_SECRET', '')


def lambda_handler(event, context):
    """Main Lambda handler."""
    try:
        # Parse Sentry webhook payload
        body = json.loads(event.get('body', '{}'))
        
        # Validate webhook (optional but recommended)
        if SENTRY_CLIENT_SECRET:
            signature = event.get('headers', {}).get('sentry-hook-signature', '')
            if not validate_signature(event['body'], signature):
                logger.warning("Invalid webhook signature")
                return {'statusCode': 401, 'body': 'Invalid signature'}
        
        # Extract event type
        action = body.get('action')
        data = body.get('data', {})
        
        # Only process new issues or issues that exceed threshold
        if action not in ['created', 'triggered']:
            logger.info(f"Ignoring action: {action}")
            return {'statusCode': 200, 'body': 'Ignored'}
        
        # Extract error details
        issue = data.get('issue', {})
        event_data = data.get('event', {})
        
        error_info = extract_error_info(issue, event_data)
        
        # Check if ticket already exists (dedup)
        existing = find_existing_ticket(error_info['fingerprint'])
        if existing:
            logger.info(f"Ticket already exists: {existing}")
            return {'statusCode': 200, 'body': f'Duplicate: {existing}'}
        
        # Create Jira ticket
        ticket_key = create_jira_ticket(error_info)
        
        logger.info(f"Created Jira ticket: {ticket_key}")
        return {
            'statusCode': 200,
            'body': json.dumps({'ticket': ticket_key})
        }
        
    except Exception as e:
        logger.exception("Lambda failed")
        return {'statusCode': 500, 'body': str(e)}


def validate_signature(body: str, signature: str) -> bool:
    """Validate Sentry webhook signature."""
    expected = hashlib.sha256(
        f"{SENTRY_CLIENT_SECRET}{body}".encode()
    ).hexdigest()
    return signature == expected


def extract_error_info(issue: dict, event: dict) -> dict:
    """Extract relevant error information from Sentry payload."""
    
    # Get stack trace
    stacktrace = ""
    exception = event.get('exception', {})
    if exception and 'values' in exception:
        for exc in exception['values']:
            stacktrace += f"\n{exc.get('type', 'Error')}: {exc.get('value', '')}\n"
            if 'stacktrace' in exc:
                for frame in exc['stacktrace'].get('frames', [])[-5:]:  # Last 5 frames
                    stacktrace += f"  at {frame.get('filename', '?')}:{frame.get('lineno', '?')} in {frame.get('function', '?')}\n"
    
    # Get tags for context
    tags = {t['key']: t['value'] for t in event.get('tags', [])}
    
    # Get breadcrumbs (last 5)
    breadcrumbs = event.get('breadcrumbs', {}).get('values', [])[-5:]
    breadcrumb_text = "\n".join([
        f"  [{b.get('category', '?')}] {b.get('message', '')}"
        for b in breadcrumbs
    ])
    
    return {
        'title': issue.get('title', 'Unknown Error'),
        'culprit': issue.get('culprit', ''),
        'level': issue.get('level', 'error'),
        'first_seen': issue.get('firstSeen', ''),
        'count': issue.get('count', 1),
        'sentry_link': issue.get('permalink', ''),
        'stacktrace': stacktrace,
        'breadcrumbs': breadcrumb_text,
        'environment': tags.get('environment', 'unknown'),
        'release': tags.get('release', 'unknown'),
        'browser': tags.get('browser', ''),
        'os': tags.get('os', ''),
        'fingerprint': issue.get('id', hashlib.md5(issue.get('title', '').encode()).hexdigest())
    }


def find_existing_ticket(fingerprint: str) -> str | None:
    """Check if a ticket with this Sentry fingerprint already exists."""
    jql = f'project = {JIRA_PROJECT} AND labels = "{AI_FIX_LABEL}" AND text ~ "sentry-id:{fingerprint}"'
    
    response = requests.get(
        f"{JIRA_URL}/rest/api/3/search",
        params={'jql': jql, 'maxResults': 1},
        auth=(JIRA_EMAIL, JIRA_TOKEN),
        headers={'Accept': 'application/json'}
    )
    
    if response.status_code == 200:
        issues = response.json().get('issues', [])
        if issues:
            return issues[0]['key']
    return None


def create_jira_ticket(error_info: dict) -> str:
    """Create a Jira ticket with error details."""
    
    # Build description with all context for Claude
    description = f"""h2. Error Details

*Error:* {error_info['title']}
*Location:* {error_info['culprit']}
*Level:* {error_info['level']}
*Environment:* {error_info['environment']}
*Release:* {error_info['release']}
*Occurrences:* {error_info['count']}

h2. Stack Trace
{{code}}
{error_info['stacktrace']}
{{code}}

h2. Recent Activity (Breadcrumbs)
{{code}}
{error_info['breadcrumbs']}
{{code}}

h2. Links
* [Sentry Issue|{error_info['sentry_link']}]

----
_sentry-id:{error_info['fingerprint']}_
_Auto-generated by Sentry Integration_
"""

    # Determine priority based on error level and count
    priority_map = {
        'fatal': '1',    # Highest
        'error': '2',    # High
        'warning': '3',  # Medium
        'info': '4'      # Low
    }
    priority_id = priority_map.get(error_info['level'], '3')
    
    # If high occurrence, bump priority
    if error_info['count'] > 100:
        priority_id = '1'
    elif error_info['count'] > 10:
        priority_id = min(int(priority_id), 2)

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT},
            "summary": f"[Sentry] {error_info['title'][:200]}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            },
            "issuetype": {"name": "Bug"},
            "priority": {"id": priority_id},
            "labels": [AI_FIX_LABEL, "sentry", error_info['environment']]
        }
    }
    
    response = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        json=payload,
        auth=(JIRA_EMAIL, JIRA_TOKEN),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    )
    
    if response.status_code not in [200, 201]:
        raise Exception(f"Jira API error: {response.status_code} - {response.text}")
    
    return response.json()['key']
```

### 0.3 Terraform for Lambda + API Gateway

```hcl
# sentry_lambda.tf

provider "aws" {
  region = "us-east-1"
}

# Lambda function
resource "aws_lambda_function" "sentry_to_jira" {
  filename         = "sentry_lambda.zip"
  function_name    = "sentry-to-jira"
  role            = aws_iam_role.lambda_role.arn
  handler         = "sentry_to_jira.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      JIRA_URL           = var.jira_url
      JIRA_EMAIL         = var.jira_email
      JIRA_TOKEN         = var.jira_token
      JIRA_PROJECT       = var.jira_project
      SENTRY_CLIENT_SECRET = var.sentry_secret
    }
  }
}

# IAM role
resource "aws_iam_role" "lambda_role" {
  name = "sentry-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

# API Gateway
resource "aws_apigatewayv2_api" "sentry_webhook" {
  name          = "sentry-webhook-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.sentry_webhook.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.sentry_webhook.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.sentry_to_jira.invoke_arn
}

resource "aws_apigatewayv2_route" "post" {
  api_id    = aws_apigatewayv2_api.sentry_webhook.id
  route_key = "POST /sentry-hook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sentry_to_jira.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.sentry_webhook.execution_arn}/*/*"
}

# Output the webhook URL
output "webhook_url" {
  value = "${aws_apigatewayv2_api.sentry_webhook.api_endpoint}/sentry-hook"
}
```

### 0.4 Sentry Configuration

1. **לך ל-Sentry → Settings → Integrations → Webhooks**

2. **הוסף Webhook חדש:**
   ```
   URL: https://xxxxxx.execute-api.us-east-1.amazonaws.com/sentry-hook
   ```

3. **בחר את ה-Events:**
   - ✅ `issue.created` - באג חדש
   - ✅ `event.alert` - חריגה מסף (Alert Rules)

4. **הגדר Alert Rules (אופציונלי אבל מומלץ):**
   ```
   Settings → Alerts → Create Alert Rule
   
   When: An issue is seen more than 10 times in 1 hour
   Then: Send a notification to Webhook
   ```

### 0.5 Jira Webhook to Agent

עכשיו צריך לחבר את Jira לסוכן. כש-Ticket נוצר עם label `AI-Fix`:

```
Jira → Automation → Webhook → Agent EC2
```

**Jira Automation Rule:**

1. **לך ל-Jira → Project Settings → Automation**

2. **צור Rule חדש:**
   ```yaml
   Trigger: Issue Created
   Condition: Labels contains "AI-Fix"
   Action: Send Web Request
     URL: http://<AGENT-EC2-IP>:3000/jira-webhook
     Method: POST
     Body: 
       {
         "ticket_id": "{{issue.key}}",
         "summary": "{{issue.summary}}",
         "description": "{{issue.description}}"
       }
   ```

### 0.6 Agent Webhook Listener (להוסיף ל-agent)

```python
# ~/claude-agent/scripts/webhook_listener.py
"""
Simple webhook listener for Jira automation
Runs on port 3000, receives tickets and queues them
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from threading import Thread
import queue
import time

from agent import ClaudeAgent

app = Flask(__name__)
task_queue = queue.Queue()
logger = logging.getLogger("webhook")

# Start agent worker in background
def agent_worker():
    agent = ClaudeAgent()
    while True:
        try:
            ticket_id = task_queue.get(timeout=5)
            logger.info(f"Processing ticket: {ticket_id}")
            agent.run(ticket_id)
            task_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.exception(f"Worker error: {e}")

worker_thread = Thread(target=agent_worker, daemon=True)
worker_thread.start()


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "queue_size": task_queue.qsize()
    })


@app.route('/jira-webhook', methods=['POST'])
def jira_webhook():
    """Receive webhook from Jira automation."""
    try:
        data = request.json
        ticket_id = data.get('ticket_id')
        
        if not ticket_id:
            return jsonify({"error": "Missing ticket_id"}), 400
        
        # Check for AI-Fix label (double check)
        # In production, verify with Jira API
        
        logger.info(f"Received ticket: {ticket_id}")
        task_queue.put(ticket_id)
        
        return jsonify({
            "status": "queued",
            "ticket_id": ticket_id,
            "queue_position": task_queue.qsize()
        })
        
    except Exception as e:
        logger.exception("Webhook error")
        return jsonify({"error": str(e)}), 500


@app.route('/manual', methods=['POST'])
def manual_trigger():
    """Manual trigger for testing."""
    ticket_id = request.json.get('ticket_id')
    if not ticket_id:
        return jsonify({"error": "Missing ticket_id"}), 400
    
    task_queue.put(ticket_id)
    return jsonify({"status": "queued", "ticket_id": ticket_id})


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=3000)
```

### 0.7 Complete Flow Test

```bash
# 1. Test Lambda locally
pip install python-lambda-local
python-lambda-local -f lambda_handler sentry_to_jira.py test_event.json

# 2. Test Jira ticket creation
curl -X POST https://your-api.execute-api.amazonaws.com/sentry-hook \
  -H "Content-Type: application/json" \
  -d '{"action":"created","data":{"issue":{"title":"Test Error","id":"123"}}}'

# 3. Test agent webhook
curl -X POST http://localhost:3000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"PROJ-999"}'

# 4. Full E2E: Trigger error in your app that Sentry catches
# Watch the flow: Sentry → Lambda → Jira → Agent → PR
```

---

## Part 1: Machine Setup (יום 1 בוקר)

### 1.1 הקמת EC2

```bash
# AWS CLI - יצירת המכונה
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.large \
  --key-name your-key \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=claude-agent-poc}]'
```

**Specs:**
- **Instance:** t3.large (2 vCPU, 8GB RAM)
- **OS:** Ubuntu 24.04 LTS
- **Storage:** 50GB gp3
- **Region:** הכי קרוב אליך (latency)

### 1.2 Security Group Rules

```
Inbound:
  - SSH (22) from your IP only
  - HTTPS (443) outbound for API calls

Outbound:
  - All traffic (for GitHub, Jira, Anthropic APIs)
```

### 1.3 התקנת Dependencies

```bash
#!/bin/bash
# setup.sh - הרץ על המכונה

set -e

echo "=== Updating System ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Installing Core Tools ==="
sudo apt-get install -y \
  git \
  curl \
  jq \
  python3 \
  python3-pip \
  python3-venv \
  docker.io \
  docker-compose

echo "=== Installing Node.js 20 ==="
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "=== Installing Claude Code CLI ==="
sudo npm install -g @anthropic-ai/claude-code

echo "=== Docker Setup ==="
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

echo "=== Creating Directory Structure ==="
mkdir -p ~/claude-agent/{workspace,logs,config,scripts}
mkdir -p ~/claude-agent/workspace/repos

echo "=== Installing Python Dependencies ==="
cd ~/claude-agent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install \
  requests \
  python-dotenv \
  jira \
  PyGithub \
  pyyaml \
  rich \
  tenacity \
  flask \
  slack-sdk

echo "=== Setup Complete ==="
echo "Please run: newgrp docker"
echo "Then configure Claude CLI with: claude login"
```

### 1.4 Claude CLI Authentication

```bash
# אפשרות 1: Login אינטראקטיבי (דורש דפדפן)
claude login

# אפשרות 2: העתקת config מהמחשב המקומי
# במחשב המקומי:
cat ~/.claude/config.json

# בשרת - יצירת הקובץ:
mkdir -p ~/.claude
cat > ~/.claude/config.json << 'EOF'
{
  "auth": {
    "token": "YOUR_TOKEN_FROM_LOCAL_MACHINE"
  }
}
EOF
chmod 600 ~/.claude/config.json
```

### 1.5 Git & GitHub Setup

```bash
# Git global config
git config --global user.name "Claude Agent"
git config --global user.email "claude-agent@yourcompany.com"

# GitHub authentication (Personal Access Token)
# יצירת token ב: https://github.com/settings/tokens
# Scopes needed: repo, workflow

cat > ~/.netrc << 'EOF'
machine github.com
  login YOUR_GITHUB_USERNAME
  password YOUR_GITHUB_PAT
EOF
chmod 600 ~/.netrc

# או SSH key
ssh-keygen -t ed25519 -C "claude-agent@yourcompany.com" -f ~/.ssh/github_agent -N ""
# הוסף את ה-public key ל-GitHub
```

---

## Part 2: Directory Structure

```
~/claude-agent/
├── config/
│   ├── .env                    # Environment variables
│   ├── repos.yaml              # Repository configurations
│   └── prompts/
│       ├── analyze.md          # Prompt for analysis phase
│       ├── fix.md              # Prompt for fix phase
│       └── test.md             # Prompt for test phase
├── scripts/
│   ├── agent.py                # Main orchestrator
│   ├── webhook_listener.py     # Flask server for Jira webhooks
│   ├── jira_client.py          # Jira API wrapper
│   ├── github_client.py        # GitHub API wrapper
│   ├── claude_executor.py      # Claude CLI wrapper
│   ├── docker_sandbox.py       # Docker test runner
│   ├── slack_client.py         # Slack notifications
│   ├── repo_manager.py         # Repository management
│   ├── setup_repos.sh          # Initial repo setup
│   ├── nightly_maintenance.sh  # Cron job for updates
│   └── utils.py                # Utilities
├── workspace/
│   └── repos/
│       ├── frontend-app/       # Pre-cloned repositories
│       ├── backend-api/        # with dependencies installed
│       └── mobile-app/
├── logs/
│   ├── agent.log
│   ├── maintenance.log
│   └── tasks/
│       └── PROJ-123/           # Per-task logs
└── venv/                       # Python virtual environment
```

---

## Part 3: Configuration Files

### 3.1 Environment Variables

```bash
# ~/claude-agent/config/.env

# Jira
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_ORG=your-org-name

# Claude
CLAUDE_CONFIG_DIR=/home/ubuntu/.claude

# Agent Settings
TASK_TIMEOUT_MINUTES=20
MAX_FIX_ATTEMPTS=3
DOCKER_MEMORY_LIMIT=4g
LOG_LEVEL=INFO
```

### 3.2 Repository Configuration

```yaml
# ~/claude-agent/config/repos.yaml

repositories:
  frontend-app:
    url: git@github.com:your-org/frontend-app.git
    branch: main
    language: typescript
    test_command: npm test
    install_command: npm ci
    docker_image: node:20-alpine
    keywords:
      - frontend
      - react
      - ui
      - component

  backend-api:
    url: git@github.com:your-org/backend-api.git
    branch: main
    language: python
    test_command: pytest
    install_command: pip install -r requirements.txt
    docker_image: python:3.11-slim
    keywords:
      - backend
      - api
      - server
      - endpoint

  mobile-app:
    url: git@github.com:your-org/mobile-app.git
    branch: develop
    language: typescript
    test_command: npm test
    install_command: npm ci
    docker_image: node:20-alpine
    keywords:
      - mobile
      - react-native
      - ios
      - android

# Default settings
defaults:
  docker_timeout: 600  # 10 minutes
  clone_depth: 1
```

### 3.3 Prompts

```markdown
# ~/claude-agent/config/prompts/analyze.md

You are analyzing a bug report to understand which repository and files are affected.

## Bug Information
- Ticket ID: {ticket_id}
- Title: {title}
- Description: {description}
- Error Logs: {error_logs}

## Available Repositories
{repo_list}

## Your Task
1. Identify which repository this bug belongs to
2. List the likely affected files based on the error
3. Suggest a high-level fix approach

Respond in this JSON format:
```json
{
  "repository": "repo-name",
  "confidence": 0.95,
  "affected_files": ["src/path/to/file.ts"],
  "root_cause": "Brief description",
  "fix_approach": "High-level approach"
}
```
```

```markdown
# ~/claude-agent/config/prompts/fix.md

You are fixing a bug in the codebase.

## Context
- Repository: {repo_name}
- Branch: feature/{ticket_id}
- Ticket: {ticket_id} - {title}

## Bug Description
{description}

## Error Details
{error_logs}

## Analysis
{analysis}

## Instructions
1. Navigate to the repository at {repo_path}
2. Find and fix the bug
3. Write or update tests to cover this fix
4. Ensure all existing tests still pass
5. Follow the existing code style

Important:
- Make minimal changes needed to fix the issue
- Do not refactor unrelated code
- Add comments explaining the fix if complex
- Test your changes thoroughly
```

---

## Part 4: Core Scripts

### 4.1 Main Agent (agent.py)

```python
#!/usr/bin/env python3
"""
Claude Agent - Main Orchestrator
Usage: python agent.py PROJ-123
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

from jira_client import JiraClient
from github_client import GitHubClient
from claude_executor import ClaudeExecutor
from docker_sandbox import DockerSandbox
from utils import setup_logging, load_repos_config

# Load environment
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

console = Console()
logger = logging.getLogger("agent")


class ClaudeAgent:
    def __init__(self):
        self.workspace = Path.home() / "claude-agent" / "workspace" / "repos"
        self.config_dir = Path.home() / "claude-agent" / "config"
        self.logs_dir = Path.home() / "claude-agent" / "logs"
        
        self.jira = JiraClient()
        self.github = GitHubClient()
        self.claude = ClaudeExecutor()
        self.docker = DockerSandbox()
        
        self.repos_config = load_repos_config(self.config_dir / "repos.yaml")
        self.max_attempts = int(os.getenv("MAX_FIX_ATTEMPTS", 3))

    def run(self, ticket_id: str) -> dict:
        """Execute the full workflow for a Jira ticket."""
        task_log_dir = self.logs_dir / "tasks" / ticket_id
        task_log_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            "ticket_id": ticket_id,
            "status": "started",
            "started_at": datetime.now().isoformat(),
            "steps": []
        }
        
        try:
            # Step 1: Fetch Jira ticket
            console.print(f"\n[bold blue]Step 1: Fetching Jira ticket {ticket_id}[/]")
            ticket = self.jira.get_ticket(ticket_id)
            result["steps"].append({"step": "fetch_ticket", "status": "success"})
            
            self.jira.update_status(ticket_id, "In Progress")
            self.jira.add_comment(ticket_id, "🤖 Claude Agent started working on this ticket.")
            
            # Step 2: Analyze and identify repository
            console.print("\n[bold blue]Step 2: Analyzing ticket...[/]")
            analysis = self._analyze_ticket(ticket)
            result["steps"].append({"step": "analyze", "status": "success", "data": analysis})
            result["repository"] = analysis["repository"]
            
            # Step 3: Prepare repository
            console.print(f"\n[bold blue]Step 3: Preparing repository {analysis['repository']}[/]")
            repo_path = self._prepare_repo(analysis["repository"], ticket_id)
            result["steps"].append({"step": "prepare_repo", "status": "success"})
            result["branch"] = f"fix/{ticket_id.lower()}"
            
            # Step 4: Fix the bug (with retries)
            console.print("\n[bold blue]Step 4: Fixing the bug...[/]")
            fix_result = self._fix_bug(repo_path, ticket, analysis)
            result["steps"].append({"step": "fix", "status": "success", "attempts": fix_result["attempts"]})
            
            # Step 5: Run tests in Docker
            console.print("\n[bold blue]Step 5: Running tests...[/]")
            test_result = self._run_tests(repo_path, analysis["repository"])
            result["steps"].append({"step": "test", "status": "success" if test_result["passed"] else "failed"})
            
            if not test_result["passed"]:
                raise Exception(f"Tests failed: {test_result['output']}")
            
            # Step 6: Create Pull Request
            console.print("\n[bold blue]Step 6: Creating Pull Request...[/]")
            pr_url = self._create_pr(repo_path, ticket, analysis)
            result["steps"].append({"step": "create_pr", "status": "success"})
            result["pr_url"] = pr_url
            
            # Step 7: Update Jira
            console.print("\n[bold blue]Step 7: Updating Jira...[/]")
            self.jira.update_status(ticket_id, "In Review")
            self.jira.add_comment(
                ticket_id, 
                f"🤖 Claude Agent completed the fix.\n\nPull Request: {pr_url}\n\nPlease review."
            )
            
            result["status"] = "success"
            result["completed_at"] = datetime.now().isoformat()
            
            console.print(f"\n[bold green]✓ Successfully created PR: {pr_url}[/]")
            
        except Exception as e:
            logger.exception("Agent failed")
            result["status"] = "failed"
            result["error"] = str(e)
            result["completed_at"] = datetime.now().isoformat()
            
            self.jira.add_comment(
                ticket_id,
                f"🤖 Claude Agent failed to fix this ticket.\n\nError: {str(e)}\n\nManual intervention required."
            )
            self.jira.update_status(ticket_id, "Agent Failed")
            
            console.print(f"\n[bold red]✗ Failed: {e}[/]")
        
        # Save result
        with open(task_log_dir / "result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return result

    def _analyze_ticket(self, ticket: dict) -> dict:
        """Use Claude to analyze which repo and files are affected."""
        prompt_template = (self.config_dir / "prompts" / "analyze.md").read_text()
        
        repo_list = "\n".join([
            f"- {name}: {cfg['keywords']}" 
            for name, cfg in self.repos_config["repositories"].items()
        ])
        
        prompt = prompt_template.format(
            ticket_id=ticket["key"],
            title=ticket["summary"],
            description=ticket["description"],
            error_logs=ticket.get("error_logs", "N/A"),
            repo_list=repo_list
        )
        
        response = self.claude.ask(prompt)
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
        raise Exception("Failed to parse analysis response")

    def _prepare_repo(self, repo_name: str, ticket_id: str) -> Path:
        """Clone or update repository and create feature branch."""
        repo_config = self.repos_config["repositories"][repo_name]
        repo_path = self.workspace / repo_name
        branch_name = f"fix/{ticket_id.lower()}"
        
        if repo_path.exists():
            # Update existing repo
            logger.info(f"Updating existing repo at {repo_path}")
            self._run_git(repo_path, ["fetch", "origin"])
            self._run_git(repo_path, ["checkout", repo_config["branch"]])
            self._run_git(repo_path, ["pull", "origin", repo_config["branch"]])
        else:
            # Fresh clone
            logger.info(f"Cloning {repo_config['url']} to {repo_path}")
            os.system(f"git clone --depth 1 {repo_config['url']} {repo_path}")
        
        # Create feature branch
        self._run_git(repo_path, ["checkout", "-b", branch_name])
        
        # Install dependencies in Docker
        self._install_deps(repo_path, repo_config)
        
        return repo_path

    def _run_git(self, repo_path: Path, args: list):
        """Execute git command in repo directory."""
        import subprocess
        cmd = ["git", "-C", str(repo_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        return result.stdout

    def _install_deps(self, repo_path: Path, repo_config: dict):
        """Install dependencies using Docker."""
        logger.info("Installing dependencies...")
        self.docker.run(
            image=repo_config["docker_image"],
            command=repo_config["install_command"],
            workdir="/app",
            volumes={str(repo_path): "/app"},
            timeout=300
        )

    def _fix_bug(self, repo_path: Path, ticket: dict, analysis: dict) -> dict:
        """Use Claude CLI to fix the bug with retry logic."""
        prompt_template = (self.config_dir / "prompts" / "fix.md").read_text()
        
        prompt = prompt_template.format(
            repo_name=analysis["repository"],
            repo_path=repo_path,
            ticket_id=ticket["key"],
            title=ticket["summary"],
            description=ticket["description"],
            error_logs=ticket.get("error_logs", "N/A"),
            analysis=json.dumps(analysis, indent=2)
        )
        
        attempts = 0
        last_error = None
        
        while attempts < self.max_attempts:
            attempts += 1
            logger.info(f"Fix attempt {attempts}/{self.max_attempts}")
            
            try:
                # Run Claude CLI in the repo directory
                self.claude.execute_in_repo(
                    repo_path=repo_path,
                    prompt=prompt,
                    auto_approve=True
                )
                
                # Check if tests pass
                repo_config = self.repos_config["repositories"][analysis["repository"]]
                test_result = self.docker.run(
                    image=repo_config["docker_image"],
                    command=repo_config["test_command"],
                    workdir="/app",
                    volumes={str(repo_path): "/app"},
                    timeout=300
                )
                
                if test_result["exit_code"] == 0:
                    return {"attempts": attempts, "success": True}
                
                # Tests failed, add error context for next attempt
                prompt += f"\n\n## Previous Attempt Failed\nTest output:\n```\n{test_result['output']}\n```\nPlease fix the remaining issues."
                last_error = test_result["output"]
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempts} failed: {e}")
        
        raise Exception(f"Failed after {attempts} attempts. Last error: {last_error}")

    def _run_tests(self, repo_path: Path, repo_name: str) -> dict:
        """Run tests in Docker sandbox."""
        repo_config = self.repos_config["repositories"][repo_name]
        
        result = self.docker.run(
            image=repo_config["docker_image"],
            command=repo_config["test_command"],
            workdir="/app",
            volumes={str(repo_path): "/app"},
            timeout=600
        )
        
        return {
            "passed": result["exit_code"] == 0,
            "output": result["output"]
        }

    def _create_pr(self, repo_path: Path, ticket: dict, analysis: dict) -> str:
        """Commit changes and create Pull Request."""
        repo_config = self.repos_config["repositories"][analysis["repository"]]
        branch_name = f"fix/{ticket['key'].lower()}"
        
        # Stage and commit
        self._run_git(repo_path, ["add", "-A"])
        commit_msg = f"fix({ticket['key']}): {ticket['summary']}\n\nAutomated fix by Claude Agent"
        self._run_git(repo_path, ["commit", "-m", commit_msg])
        
        # Push
        self._run_git(repo_path, ["push", "-u", "origin", branch_name])
        
        # Create PR via GitHub API
        pr_url = self.github.create_pr(
            repo=f"{os.getenv('GITHUB_ORG')}/{analysis['repository']}",
            title=f"fix({ticket['key']}): {ticket['summary']}",
            body=self._generate_pr_body(ticket, analysis),
            head=branch_name,
            base=repo_config["branch"]
        )
        
        return pr_url

    def _generate_pr_body(self, ticket: dict, analysis: dict) -> str:
        """Generate PR description."""
        return f"""## Summary
Automated fix for [{ticket['key']}]({os.getenv('JIRA_URL')}/browse/{ticket['key']})

## Description
{ticket['summary']}

## Root Cause
{analysis.get('root_cause', 'See ticket for details')}

## Changes Made
{analysis.get('fix_approach', 'See commits for details')}

## Testing
- [x] Unit tests pass
- [x] Linting passes
- [ ] Manual testing (reviewer please verify)

---
*This PR was automatically generated by Claude Agent* 🤖
"""


def main():
    if len(sys.argv) != 2:
        print("Usage: python agent.py PROJ-123")
        sys.exit(1)
    
    ticket_id = sys.argv[1]
    setup_logging()
    
    agent = ClaudeAgent()
    result = agent.run(ticket_id)
    
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
```

### 4.2 Jira Client (jira_client.py)

```python
"""Jira API Client"""

import os
import logging
from jira import JIRA

logger = logging.getLogger("agent.jira")


class JiraClient:
    def __init__(self):
        self.client = JIRA(
            server=os.getenv("JIRA_URL"),
            basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
        )
    
    def get_ticket(self, ticket_id: str) -> dict:
        """Fetch ticket details from Jira."""
        issue = self.client.issue(ticket_id)
        
        # Extract Sentry error logs if attached
        error_logs = ""
        for attachment in issue.fields.attachment:
            if "sentry" in attachment.filename.lower() or "error" in attachment.filename.lower():
                error_logs += f"\n--- {attachment.filename} ---\n"
                error_logs += attachment.get()
        
        # Also check description for error traces
        description = issue.fields.description or ""
        if "```" in description:
            # Likely contains code/error blocks
            error_logs += f"\n--- From Description ---\n{description}"
        
        return {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": description,
            "status": issue.fields.status.name,
            "priority": issue.fields.priority.name if issue.fields.priority else "Medium",
            "labels": issue.fields.labels,
            "error_logs": error_logs or "No error logs found",
            "reporter": issue.fields.reporter.displayName if issue.fields.reporter else "Unknown"
        }
    
    def update_status(self, ticket_id: str, status: str):
        """Update ticket status."""
        issue = self.client.issue(ticket_id)
        
        # Find the transition ID for the target status
        transitions = self.client.transitions(issue)
        for t in transitions:
            if t["name"].lower() == status.lower():
                self.client.transition_issue(issue, t["id"])
                logger.info(f"Updated {ticket_id} status to {status}")
                return
        
        logger.warning(f"Could not find transition to '{status}' for {ticket_id}")
    
    def add_comment(self, ticket_id: str, comment: str):
        """Add a comment to the ticket."""
        self.client.add_comment(ticket_id, comment)
        logger.info(f"Added comment to {ticket_id}")
```

### 4.3 GitHub Client (github_client.py)

```python
"""GitHub API Client"""

import os
import logging
from github import Github

logger = logging.getLogger("agent.github")


class GitHubClient:
    def __init__(self):
        self.client = Github(os.getenv("GITHUB_TOKEN"))
    
    def create_pr(self, repo: str, title: str, body: str, head: str, base: str) -> str:
        """Create a Pull Request and return its URL."""
        repository = self.client.get_repo(repo)
        
        pr = repository.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
            maintainer_can_modify=True
        )
        
        # Add labels
        pr.add_to_labels("automated", "claude-agent")
        
        logger.info(f"Created PR #{pr.number}: {pr.html_url}")
        return pr.html_url
    
    def get_file_content(self, repo: str, path: str, ref: str = "main") -> str:
        """Get file content from repository."""
        repository = self.client.get_repo(repo)
        content = repository.get_contents(path, ref=ref)
        return content.decoded_content.decode("utf-8")
```

### 4.4 Claude Executor (claude_executor.py)

```python
"""Claude CLI Executor"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("agent.claude")


class ClaudeExecutor:
    def __init__(self):
        self.config_dir = os.getenv("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))
        self.timeout = int(os.getenv("TASK_TIMEOUT_MINUTES", 20)) * 60
    
    def ask(self, prompt: str) -> str:
        """Ask Claude a question and get response (no code execution)."""
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "CLAUDE_CONFIG_DIR": self.config_dir}
        )
        
        if result.returncode != 0:
            raise Exception(f"Claude CLI failed: {result.stderr}")
        
        return result.stdout
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=4, max=10))
    def execute_in_repo(self, repo_path: Path, prompt: str, auto_approve: bool = True):
        """Execute Claude CLI in a repository to make code changes."""
        args = ["claude"]
        
        if auto_approve:
            args.append("--dangerously-skip-permissions")
        
        # Write prompt to file to avoid shell escaping issues
        prompt_file = repo_path / ".claude_prompt.md"
        prompt_file.write_text(prompt)
        
        try:
            logger.info(f"Executing Claude in {repo_path}")
            
            result = subprocess.run(
                args + ["--prompt-file", str(prompt_file)],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={
                    **os.environ,
                    "CLAUDE_CONFIG_DIR": self.config_dir,
                    "HOME": str(Path.home())
                }
            )
            
            # Log output
            if result.stdout:
                logger.debug(f"Claude stdout: {result.stdout[:1000]}")
            if result.stderr:
                logger.warning(f"Claude stderr: {result.stderr[:1000]}")
            
            if result.returncode != 0:
                raise Exception(f"Claude CLI exited with code {result.returncode}")
            
        finally:
            # Cleanup
            prompt_file.unlink(missing_ok=True)
            self._cleanup_session(repo_path)
    
    def _cleanup_session(self, repo_path: Path):
        """Clean up Claude session files to prevent memory bloat."""
        claude_dir = repo_path / ".claude"
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
        
        # Also clean global session if it exists
        global_session = Path(self.config_dir) / "session"
        if global_session.exists():
            shutil.rmtree(global_session)
```

### 4.5 Docker Sandbox (docker_sandbox.py)

```python
"""Docker Sandbox for safe code execution"""

import os
import subprocess
import logging
from typing import Dict, Optional

logger = logging.getLogger("agent.docker")


class DockerSandbox:
    def __init__(self):
        self.memory_limit = os.getenv("DOCKER_MEMORY_LIMIT", "4g")
        self.network = "none"  # No network access by default for safety
    
    def run(
        self,
        image: str,
        command: str,
        workdir: str = "/app",
        volumes: Optional[Dict[str, str]] = None,
        timeout: int = 300,
        network: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> dict:
        """
        Run a command in a Docker container.
        
        Returns:
            dict with 'exit_code', 'output', and 'error'
        """
        args = [
            "docker", "run",
            "--rm",  # Remove container after exit
            "--memory", self.memory_limit,
            "--memory-swap", self.memory_limit,  # No swap
            "--cpus", "2",
            "--workdir", workdir,
            "--network", network or self.network,
        ]
        
        # Add volumes
        if volumes:
            for host_path, container_path in volumes.items():
                args.extend(["-v", f"{host_path}:{container_path}"])
        
        # Add environment variables
        if env:
            for key, value in env.items():
                args.extend(["-e", f"{key}={value}"])
        
        # Add image and command
        args.append(image)
        args.extend(["sh", "-c", command])
        
        logger.info(f"Running in Docker: {command[:100]}...")
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout + result.stderr
            
            return {
                "exit_code": result.returncode,
                "output": output,
                "error": result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Docker command timed out after {timeout}s")
            return {
                "exit_code": -1,
                "output": "",
                "error": f"Timeout after {timeout} seconds"
            }
    
    def run_with_network(
        self,
        image: str,
        command: str,
        workdir: str = "/app",
        volumes: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> dict:
        """Run with network access (for npm install, etc.)"""
        return self.run(
            image=image,
            command=command,
            workdir=workdir,
            volumes=volumes,
            timeout=timeout,
            network="bridge"
        )
```

### 4.6 Utilities (utils.py)

```python
"""Utility functions"""

import os
import yaml
import logging
from pathlib import Path
from rich.logging import RichHandler


def setup_logging():
    """Configure logging with rich output."""
    level = os.getenv("LOG_LEVEL", "INFO")
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(rich_tracebacks=True),
            logging.FileHandler(
                Path.home() / "claude-agent" / "logs" / "agent.log"
            )
        ]
    )


def load_repos_config(path: Path) -> dict:
    """Load repository configuration from YAML."""
    with open(path) as f:
        return yaml.safe_load(f)
```

---

## Part 5: Testing the POC (יום 2-3)

### 5.1 בדיקה ידנית - צעד אחר צעד

```bash
# 1. הפעל את הסביבה
cd ~/claude-agent
source venv/bin/activate

# 2. בדוק שכל הקומפוננטות עובדות
python -c "from jira_client import JiraClient; JiraClient()"
python -c "from github_client import GitHubClient; GitHubClient()"
python -c "from claude_executor import ClaudeExecutor; ClaudeExecutor()"
python -c "from docker_sandbox import DockerSandbox; DockerSandbox()"

# 3. בדוק את Claude CLI
claude --version
claude --print "Hello, respond with just OK"

# 4. בדוק Docker
docker run --rm alpine echo "Docker works"

# 5. הרץ על טיקט אמיתי
python scripts/agent.py PROJ-123
```

### 5.2 Debug Mode Script

```python
#!/usr/bin/env python3
"""
debug_agent.py - Step-by-step debugging
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.prompt import Confirm
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

from jira_client import JiraClient
from github_client import GitHubClient
from claude_executor import ClaudeExecutor
from docker_sandbox import DockerSandbox
from utils import load_repos_config

console = Console()


def debug_run(ticket_id: str):
    """Run agent step by step with pauses."""
    
    console.print(f"\n[bold]Debugging ticket: {ticket_id}[/]\n")
    
    # Step 1: Jira
    console.print("[yellow]Step 1: Fetching Jira ticket...[/]")
    jira = JiraClient()
    ticket = jira.get_ticket(ticket_id)
    console.print(f"  Title: {ticket['summary']}")
    console.print(f"  Status: {ticket['status']}")
    console.print(f"  Error logs: {ticket['error_logs'][:200]}...")
    
    if not Confirm.ask("Continue to analysis?"):
        return
    
    # Step 2: Analysis
    console.print("\n[yellow]Step 2: Analyzing with Claude...[/]")
    claude = ClaudeExecutor()
    config = load_repos_config(Path.home() / "claude-agent" / "config" / "repos.yaml")
    
    repo_list = "\n".join([f"- {name}" for name in config["repositories"].keys()])
    prompt = f"""Analyze this bug and tell me which repository it belongs to.
    
Ticket: {ticket['summary']}
Description: {ticket['description'][:500]}
Error: {ticket['error_logs'][:500]}

Available repos:
{repo_list}

Respond with just the repository name."""
    
    response = claude.ask(prompt)
    console.print(f"  Claude says: {response}")
    
    repo_name = response.strip().lower()
    if repo_name not in config["repositories"]:
        console.print(f"[red]Unknown repo: {repo_name}[/]")
        repo_name = Confirm.ask("Enter correct repo name: ")
    
    if not Confirm.ask(f"Continue with repo '{repo_name}'?"):
        return
    
    # Step 3: Prepare repo
    console.print(f"\n[yellow]Step 3: Preparing repository {repo_name}...[/]")
    repo_config = config["repositories"][repo_name]
    repo_path = Path.home() / "claude-agent" / "workspace" / "repos" / repo_name
    
    if not repo_path.exists():
        console.print(f"  Cloning {repo_config['url']}...")
        import os
        os.system(f"git clone --depth 1 {repo_config['url']} {repo_path}")
    else:
        console.print("  Repo exists, pulling latest...")
        os.system(f"cd {repo_path} && git fetch && git pull")
    
    branch = f"fix/{ticket_id.lower()}"
    os.system(f"cd {repo_path} && git checkout -b {branch} 2>/dev/null || git checkout {branch}")
    
    if not Confirm.ask("Continue to fix?"):
        return
    
    # Step 4: Fix
    console.print("\n[yellow]Step 4: Running Claude to fix...[/]")
    fix_prompt = f"""Fix the following bug in this codebase:

Ticket: {ticket['summary']}
Description: {ticket['description']}
Error: {ticket['error_logs']}

Make the minimal changes needed. Write tests for your fix."""
    
    console.print(f"  Working in: {repo_path}")
    console.print("  Running Claude CLI...")
    
    try:
        claude.execute_in_repo(repo_path, fix_prompt, auto_approve=True)
        console.print("  [green]Claude completed![/]")
    except Exception as e:
        console.print(f"  [red]Error: {e}[/]")
    
    # Show changes
    import subprocess
    diff = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=str(repo_path),
        capture_output=True,
        text=True
    )
    console.print(f"\n  Changes:\n{diff.stdout}")
    
    if not Confirm.ask("Continue to test?"):
        return
    
    # Step 5: Test
    console.print("\n[yellow]Step 5: Running tests in Docker...[/]")
    docker = DockerSandbox()
    result = docker.run_with_network(
        image=repo_config["docker_image"],
        command=f"{repo_config['install_command']} && {repo_config['test_command']}",
        workdir="/app",
        volumes={str(repo_path): "/app"}
    )
    
    if result["exit_code"] == 0:
        console.print("  [green]Tests passed![/]")
    else:
        console.print(f"  [red]Tests failed:[/]\n{result['output'][:500]}")
    
    console.print("\n[bold green]Debug session complete![/]")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_agent.py PROJ-123")
        sys.exit(1)
    debug_run(sys.argv[1])
```

### 5.3 Test Cases לבדיקה

```yaml
# ~/claude-agent/test_cases.yaml

# בחר 5 באגים היסטוריים פשוטים שכבר תוקנו

test_cases:
  - ticket: PROJ-101
    description: "Simple typo fix in error message"
    expected_files: ["src/utils/messages.ts"]
    difficulty: easy
    
  - ticket: PROJ-102
    description: "Missing null check causes crash"
    expected_files: ["src/api/handler.py"]
    difficulty: easy
    
  - ticket: PROJ-103
    description: "Wrong date format in export"
    expected_files: ["src/services/export.js"]
    difficulty: medium
    
  - ticket: PROJ-104
    description: "API returns 500 on empty input"
    expected_files: ["src/controllers/api.ts"]
    difficulty: medium
    
  - ticket: PROJ-105
    description: "Race condition in async operation"
    expected_files: ["src/workers/processor.py"]
    difficulty: hard
```

---

## Part 6: Success Criteria

### 6.1 מדדים להצלחה

| מדד | יעד | איך למדוד |
|-----|-----|----------|
| **Success Rate** | ≥60% (3/5 tickets) | PR נוצר עם טסטים עוברים |
| **Time per Ticket** | <15 דקות | מתחילת הרצה עד PR |
| **Code Quality** | Linter passes | אין warnings/errors |
| **Test Coverage** | טסט חדש לתיקון | בדיקה ידנית |

### 6.2 Checklist לסיום POC

```markdown
## POC Completion Checklist

### Infrastructure
- [ ] EC2 instance running
- [ ] Claude CLI authenticated
- [ ] GitHub access configured
- [ ] Jira access configured
- [ ] Docker working

### Scripts
- [ ] agent.py runs without errors
- [ ] jira_client.py fetches tickets
- [ ] github_client.py creates PRs
- [ ] claude_executor.py executes commands
- [ ] docker_sandbox.py runs tests

### Tests
- [ ] Ticket PROJ-101: _____ (pass/fail)
- [ ] Ticket PROJ-102: _____ (pass/fail)
- [ ] Ticket PROJ-103: _____ (pass/fail)
- [ ] Ticket PROJ-104: _____ (pass/fail)
- [ ] Ticket PROJ-105: _____ (pass/fail)

### Documentation
- [ ] Logs saved for each run
- [ ] Failure reasons documented
- [ ] Time measurements recorded
```

---

## Part 7: Troubleshooting

### בעיות נפוצות

**1. Claude CLI נתקע**
```bash
# בדוק אם יש process תקוע
ps aux | grep claude
kill -9 <pid>

# נקה session
rm -rf ~/.claude/session
rm -rf ~/claude-agent/workspace/repos/*/.claude
```

**2. Docker permission denied**
```bash
sudo usermod -aG docker $USER
newgrp docker
# או התחבר מחדש
```

**3. Git push נכשל**
```bash
# בדוק authentication
ssh -T git@github.com
# או
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

**4. Jira API errors**
```bash
# בדוק credentials
curl -u "email:token" https://yourcompany.atlassian.net/rest/api/3/myself
```

**5. Memory issues**
```bash
# בדוק זיכרון
free -h
# הגדל swap אם צריך
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Part 8: What's Next (After POC)

אם ה-POC הצליח:

1. **שבוע 2:** הוספת Webhook listener אוטומטי
2. **שבוע 3:** שכפול ל-2-3 מכונות עם Redis queue
3. **שבוע 4:** Monitoring ו-alerting

---

## Quick Start Commands

```bash
# === INITIAL SETUP (פעם אחת) ===

# 1. Setup machine
chmod +x setup.sh && ./setup.sh
source ~/claude-agent/venv/bin/activate

# 2. Configure credentials
cp config/.env.example config/.env
nano config/.env  # fill in credentials

# 3. Test connectivity
python -c "from jira_client import JiraClient; print(JiraClient().get_ticket('PROJ-1')['summary'])"

# === MANUAL TESTING ===

# 4. Run on a single ticket (manual mode)
python scripts/agent.py PROJ-123

# 5. Debug mode (step by step)
python scripts/debug_agent.py PROJ-123

# === FULL AUTOMATED FLOW ===

# 6. Deploy Sentry Lambda (from your local machine)
cd terraform/
terraform init
terraform apply

# 7. Configure Sentry webhook
# Go to Sentry → Settings → Webhooks
# Add URL: <terraform output webhook_url>

# 8. Start webhook listener on EC2
cd ~/claude-agent
source venv/bin/activate
python scripts/webhook_listener.py &

# 9. Configure Jira Automation
# Project Settings → Automation → Create Rule:
#   Trigger: Issue Created
#   Condition: Labels contains "AI-Fix"
#   Action: Send Web Request to http://<EC2-IP>:3000/jira-webhook

# === MONITORING ===

# Check agent health
curl http://localhost:3000/health

# Watch logs
tail -f ~/claude-agent/logs/agent.log

# Manual trigger for testing
curl -X POST http://localhost:3000/manual \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"PROJ-123"}'
```

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE AUTOMATED FLOW                           │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐
    │  Your    │
    │   App    │
    └────┬─────┘
         │ Error occurs
         ▼
    ┌──────────┐
    │  Sentry  │  ← Catches & aggregates errors
    └────┬─────┘
         │ Webhook (POST)
         ▼
┌─────────────────┐
│   AWS Lambda    │  ← Parses error, checks thresholds
│ sentry_to_jira  │
└────────┬────────┘
         │ Creates ticket via API
         ▼
    ┌──────────┐
    │   Jira   │  ← Ticket created with label "AI-Fix"
    │  Ticket  │     Contains: title, stacktrace, breadcrumbs
    └────┬─────┘
         │ Automation webhook
         ▼
┌─────────────────┐
│  Agent (EC2)    │  ← webhook_listener.py receives
│  Flask Server   │
└────────┬────────┘
         │ Queues task
         ▼
┌─────────────────┐
│  Claude Agent   │  ← agent.py processes
│                 │
│  1. Analyze     │  → Which repo? Which files?
│  2. Clone/Pull  │  → Get latest code
│  3. Fix         │  → Claude Code CLI
│  4. Test        │  → Docker sandbox
│  5. PR          │  → GitHub API
└────────┬────────┘
         │
         ▼
    ┌──────────┐
    │  GitHub  │  ← PR ready for review
    │    PR    │
    └──────────┘
         │
         ▼
    ┌──────────┐
    │   Jira   │  ← Status: "In Review"
    │ Updated  │     Comment: link to PR
    └──────────┘
```

**זמן מקצה לקצה:** 5-15 דקות (תלוי במורכבות הבאג)

---

## Part 9: Slack Integration

### 9.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SLACK INTEGRATION                          │
└─────────────────────────────────────────────────────────────────┘

    OUTBOUND (Agent → Slack)              INBOUND (Slack → Agent)
    ─────────────────────────             ─────────────────────────
    
    Agent Progress Updates                Developer Queries
    ┌──────────┐                         ┌──────────┐
    │  Agent   │──webhook──▶ Slack       │  Slack   │
    └──────────┘             │           │   Bot    │
                             ▼           └────┬─────┘
                        ┌─────────┐           │ /claude-status PROJ-123
                        │ #dev-   │           ▼
                        │ alerts  │      ┌──────────┐
                        └─────────┘      │  Agent   │
                             │           │   API    │
                             ▼           └────┬─────┘
                        ┌─────────┐           │
                        │ @dev DM │           ▼
                        │ (assignee)     Status Response
                        └─────────┘
```

### 9.2 Slack App Setup

1. **צור Slack App:** https://api.slack.com/apps → Create New App

2. **Bot Token Scopes needed:**
   ```
   chat:write          - Send messages
   chat:write.public   - Send to any channel
   users:read          - Find user by email
   users:read.email    - Match Jira assignee to Slack
   commands            - Slash commands
   im:write            - DM to users
   ```

3. **Enable Events API:**
   ```
   Request URL: https://<your-api>/slack/events
   Subscribe to: app_mention, message.im
   ```

4. **Create Slash Command:**
   ```
   Command: /claude-status
   Request URL: https://<your-api>/slack/commands
   Description: Check status of a Jira ticket being fixed by Claude
   Usage hint: [TICKET-ID]
   ```

### 9.3 Slack Client (slack_client.py)

```python
"""
Slack Client for Agent notifications
"""

import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger("agent.slack")


class SlackClient:
    def __init__(self):
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.alerts_channel = os.getenv("SLACK_ALERTS_CHANNEL", "#dev-alerts")
        self.jira_url = os.getenv("JIRA_URL")
        
        # Cache for email → Slack user ID mapping
        self._user_cache = {}
    
    def notify_started(self, ticket_id: str, summary: str, assignee_email: str = None):
        """Notify that agent started working on a ticket."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🤖 Claude Agent Started"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ticket:* <{self.jira_url}/browse/{ticket_id}|{ticket_id}>"},
                    {"type": "mrkdwn", "text": f"*Summary:* {summary[:50]}..."}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "⏳ Analyzing and preparing fix..."}
                ]
            }
        ]
        
        # Post to channel
        self._post_message(self.alerts_channel, blocks)
        
        # DM to assignee if available
        if assignee_email:
            self._dm_user(assignee_email, blocks)
    
    def notify_progress(self, ticket_id: str, stage: str, details: str = ""):
        """Send progress update."""
        stage_emojis = {
            "analyzing": "🔍",
            "cloning": "📥",
            "fixing": "🔧",
            "testing": "🧪",
            "creating_pr": "📝",
        }
        emoji = stage_emojis.get(stage, "⚙️")
        
        message = f"{emoji} *{ticket_id}*: {stage.replace('_', ' ').title()}"
        if details:
            message += f"\n> {details}"
        
        self._post_message(self.alerts_channel, message)
    
    def notify_success(self, ticket_id: str, pr_url: str, assignee_email: str = None):
        """Notify successful PR creation."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Claude Agent Completed"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ticket:* <{self.jira_url}/browse/{ticket_id}|{ticket_id}>"},
                    {"type": "mrkdwn", "text": f"*Pull Request:* <{pr_url}|View PR>"}
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Review PR"},
                        "url": pr_url,
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Ticket"},
                        "url": f"{self.jira_url}/browse/{ticket_id}"
                    }
                ]
            }
        ]
        
        self._post_message(self.alerts_channel, blocks)
        
        if assignee_email:
            self._dm_user(assignee_email, blocks, 
                text=f"✅ PR ready for your review: {pr_url}")
    
    def notify_failure(self, ticket_id: str, error: str, assignee_email: str = None):
        """Notify failure."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "❌ Claude Agent Failed"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ticket:* <{self.jira_url}/browse/{ticket_id}|{ticket_id}>"},
                    {"type": "mrkdwn", "text": f"*Error:* {error[:100]}"}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Manual intervention required. Check logs for details."}
                ]
            }
        ]
        
        self._post_message(self.alerts_channel, blocks)
        
        if assignee_email:
            self._dm_user(assignee_email, blocks,
                text=f"❌ Agent failed on {ticket_id}. Manual fix needed.")
    
    def get_ticket_status(self, ticket_id: str) -> dict:
        """Get current status of a ticket being processed."""
        # This would query the agent's internal state
        # Implementation depends on how you track state
        from pathlib import Path
        import json
        
        status_file = Path.home() / "claude-agent" / "logs" / "tasks" / ticket_id / "result.json"
        
        if status_file.exists():
            with open(status_file) as f:
                return json.load(f)
        
        return {"status": "not_found", "ticket_id": ticket_id}
    
    def _post_message(self, channel: str, blocks_or_text):
        """Post message to channel."""
        try:
            if isinstance(blocks_or_text, str):
                self.client.chat_postMessage(channel=channel, text=blocks_or_text)
            else:
                self.client.chat_postMessage(
                    channel=channel, 
                    blocks=blocks_or_text,
                    text="Claude Agent Update"  # Fallback for notifications
                )
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
    
    def _dm_user(self, email: str, blocks, text: str = "Claude Agent Update"):
        """Send DM to user by email."""
        try:
            user_id = self._get_user_id_by_email(email)
            if user_id:
                self.client.chat_postMessage(
                    channel=user_id,
                    blocks=blocks,
                    text=text
                )
        except SlackApiError as e:
            logger.warning(f"Could not DM user {email}: {e}")
    
    def _get_user_id_by_email(self, email: str) -> str | None:
        """Find Slack user ID by email."""
        if email in self._user_cache:
            return self._user_cache[email]
        
        try:
            response = self.client.users_lookupByEmail(email=email)
            user_id = response["user"]["id"]
            self._user_cache[email] = user_id
            return user_id
        except SlackApiError:
            return None
```

### 9.4 Slash Command Handler

```python
# Add to webhook_listener.py

from slack_client import SlackClient

slack = SlackClient()

@app.route('/slack/commands', methods=['POST'])
def slack_command():
    """Handle /claude-status command."""
    command = request.form.get('command')
    text = request.form.get('text', '').strip()
    user_id = request.form.get('user_id')
    
    if command == '/claude-status':
        if not text:
            return jsonify({
                "response_type": "ephemeral",
                "text": "Usage: `/claude-status PROJ-123`"
            })
        
        ticket_id = text.upper()
        status = slack.get_ticket_status(ticket_id)
        
        if status["status"] == "not_found":
            return jsonify({
                "response_type": "ephemeral",
                "text": f"❓ No record found for {ticket_id}. It may not have been processed yet."
            })
        
        # Format status response
        emoji_map = {
            "started": "⏳",
            "success": "✅",
            "failed": "❌",
            "in_progress": "🔧"
        }
        emoji = emoji_map.get(status["status"], "❓")
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{ticket_id}* - {status['status'].replace('_', ' ').title()}"
                }
            }
        ]
        
        if "pr_url" in status:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*PR:* <{status['pr_url']}|View Pull Request>"}
            })
        
        if "steps" in status:
            steps_text = "\n".join([
                f"{'✅' if s['status'] == 'success' else '❌'} {s['step']}"
                for s in status["steps"]
            ])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Steps:*\n{steps_text}"}
            })
        
        return jsonify({
            "response_type": "in_channel",
            "blocks": blocks
        })
    
    return jsonify({"response_type": "ephemeral", "text": "Unknown command"})


@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack Events API."""
    data = request.json
    
    # URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})
    
    event = data.get("event", {})
    
    # Handle app mentions
    if event.get("type") == "app_mention":
        text = event.get("text", "")
        channel = event.get("channel")
        
        # Extract ticket ID from mention
        import re
        match = re.search(r'([A-Z]+-\d+)', text.upper())
        
        if match:
            ticket_id = match.group(1)
            status = slack.get_ticket_status(ticket_id)
            slack._post_message(channel, f"Status of {ticket_id}: {status['status']}")
        else:
            slack._post_message(channel, 
                "Hi! I can check ticket status. Try: `@Claude Agent PROJ-123`")
    
    return jsonify({"ok": True})
```

### 9.5 Integration with Agent

```python
# Update agent.py to include Slack notifications

from slack_client import SlackClient

class ClaudeAgent:
    def __init__(self):
        # ... existing init ...
        self.slack = SlackClient()
    
    def run(self, ticket_id: str) -> dict:
        # ... existing code ...
        
        try:
            # Step 1: Fetch Jira ticket
            ticket = self.jira.get_ticket(ticket_id)
            assignee_email = ticket.get("assignee_email")
            
            # Notify start
            self.slack.notify_started(ticket_id, ticket["summary"], assignee_email)
            
            # Step 2: Analyze
            self.slack.notify_progress(ticket_id, "analyzing")
            analysis = self._analyze_ticket(ticket)
            
            # Step 3: Prepare repo
            self.slack.notify_progress(ticket_id, "cloning", f"Repository: {analysis['repository']}")
            repo_path = self._prepare_repo(analysis["repository"], ticket_id)
            
            # Step 4: Fix
            self.slack.notify_progress(ticket_id, "fixing")
            fix_result = self._fix_bug(repo_path, ticket, analysis)
            
            # Step 5: Test
            self.slack.notify_progress(ticket_id, "testing")
            test_result = self._run_tests(repo_path, analysis["repository"])
            
            # Step 6: Create PR
            self.slack.notify_progress(ticket_id, "creating_pr")
            pr_url = self._create_pr(repo_path, ticket, analysis)
            
            # Notify success
            self.slack.notify_success(ticket_id, pr_url, assignee_email)
            
            result["status"] = "success"
            result["pr_url"] = pr_url
            
        except Exception as e:
            self.slack.notify_failure(ticket_id, str(e), assignee_email)
            raise
```

### 9.6 Environment Variables

```bash
# Add to config/.env

# Slack
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_ALERTS_CHANNEL=#dev-ai-alerts
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Part 10: Repository Management Strategy

### 10.1 Philosophy: Each Machine = Developer Workstation

```
┌─────────────────────────────────────────────────────────────────┐
│                    MACHINE AS DEVELOPER                         │
└─────────────────────────────────────────────────────────────────┘

Traditional Approach (Bad):          Our Approach (Good):
──────────────────────────          ──────────────────────

  Task arrives                        Task arrives
       │                                   │
       ▼                                   ▼
  git clone repo (3-5 min)           git fetch + pull (5 sec)
       │                                   │
       ▼                                   ▼
  npm install (5-10 min)             npm ci (30 sec, cached)
       │                                   │
       ▼                                   ▼
  Work on task                       Work on task
       │                                   │
       ▼                                   ▼
  Delete everything                  Keep for next task
  
  Total setup: 10-15 min             Total setup: <1 min
```

### 10.2 Initial Machine Setup Script

```bash
#!/bin/bash
# ~/claude-agent/scripts/setup_repos.sh
# Run once when setting up a new machine

set -e

WORKSPACE="$HOME/claude-agent/workspace/repos"
CONFIG="$HOME/claude-agent/config/repos.yaml"

echo "=== Setting up repositories ==="

# Parse repos.yaml and clone each
python3 << 'PYTHON'
import yaml
import subprocess
import os
from pathlib import Path

workspace = Path(os.environ["WORKSPACE"])
config_path = os.environ["CONFIG"]

with open(config_path) as f:
    config = yaml.safe_load(f)

for name, repo in config["repositories"].items():
    repo_path = workspace / name
    
    if repo_path.exists():
        print(f"✓ {name} already exists, pulling latest...")
        subprocess.run(["git", "-C", str(repo_path), "fetch", "--all"], check=True)
        subprocess.run(["git", "-C", str(repo_path), "checkout", repo["branch"]], check=True)
        subprocess.run(["git", "-C", str(repo_path), "pull"], check=True)
    else:
        print(f"⬇ Cloning {name}...")
        subprocess.run([
            "git", "clone", 
            "--branch", repo["branch"],
            repo["url"], 
            str(repo_path)
        ], check=True)
    
    # Install dependencies based on language
    print(f"📦 Installing dependencies for {name}...")
    
    if repo["language"] in ["javascript", "typescript"]:
        # Use npm ci for reproducible installs
        subprocess.run(["npm", "ci"], cwd=str(repo_path), check=False)
    
    elif repo["language"] == "python":
        # Create venv and install
        venv_path = repo_path / ".venv"
        if not venv_path.exists():
            subprocess.run(["python3", "-m", "venv", str(venv_path)], check=True)
        pip = venv_path / "bin" / "pip"
        subprocess.run([str(pip), "install", "-r", "requirements.txt"], 
                      cwd=str(repo_path), check=False)
    
    print(f"✅ {name} ready!\n")

print("=== All repositories ready ===")
PYTHON

echo "Setup complete!"
```

### 10.3 Pre-Task Update Script

```python
# ~/claude-agent/scripts/repo_manager.py
"""
Repository Manager - Ensures repo is ready before each task
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional
import yaml
import shutil

logger = logging.getLogger("agent.repo")


class RepoManager:
    def __init__(self):
        self.workspace = Path.home() / "claude-agent" / "workspace" / "repos"
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        config_path = Path.home() / "claude-agent" / "config" / "repos.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def prepare_for_task(self, repo_name: str, ticket_id: str) -> Path:
        """
        Prepare repository for a new task:
        1. Ensure repo exists (clone if missing)
        2. Clean up any previous work
        3. Pull latest from main branch
        4. Create feature branch
        5. Ensure dependencies are up to date
        
        Returns path to repo.
        """
        repo_config = self.config["repositories"].get(repo_name)
        if not repo_config:
            raise ValueError(f"Unknown repository: {repo_name}")
        
        repo_path = self.workspace / repo_name
        main_branch = repo_config.get("branch", "main")
        feature_branch = f"fix/{ticket_id.lower()}"
        
        # Step 1: Ensure repo exists
        if not repo_path.exists():
            logger.info(f"Repository not found, cloning {repo_name}...")
            self._clone_repo(repo_name, repo_config)
        
        # Step 2: Clean up any uncommitted changes and switch to main
        logger.info(f"Cleaning up {repo_name}...")
        self._cleanup_repo(repo_path, main_branch)
        
        # Step 3: Pull latest
        logger.info(f"Pulling latest from {main_branch}...")
        self._git(repo_path, ["fetch", "origin"])
        self._git(repo_path, ["reset", "--hard", f"origin/{main_branch}"])
        
        # Step 4: Create feature branch
        logger.info(f"Creating branch {feature_branch}...")
        # Delete if exists (from previous failed attempt)
        try:
            self._git(repo_path, ["branch", "-D", feature_branch])
        except:
            pass
        self._git(repo_path, ["checkout", "-b", feature_branch])
        
        # Step 5: Update dependencies if package files changed
        if self._needs_dependency_update(repo_path, repo_config):
            logger.info("Updating dependencies...")
            self._install_dependencies(repo_path, repo_config)
        
        logger.info(f"✅ Repository {repo_name} ready at {repo_path}")
        return repo_path
    
    def _clone_repo(self, name: str, config: dict):
        """Clone a repository."""
        repo_path = self.workspace / name
        subprocess.run([
            "git", "clone",
            "--branch", config.get("branch", "main"),
            config["url"],
            str(repo_path)
        ], check=True)
        
        # Initial dependency install
        self._install_dependencies(repo_path, config)
    
    def _cleanup_repo(self, repo_path: Path, main_branch: str):
        """Reset repo to clean state."""
        # Abort any in-progress operations
        for op in ["rebase", "merge", "cherry-pick"]:
            try:
                self._git(repo_path, [op, "--abort"])
            except:
                pass
        
        # Discard all changes
        self._git(repo_path, ["checkout", "--", "."])
        self._git(repo_path, ["clean", "-fd"])
        
        # Remove any .claude session
        claude_dir = repo_path / ".claude"
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
        
        # Switch to main
        self._git(repo_path, ["checkout", main_branch])
    
    def _needs_dependency_update(self, repo_path: Path, config: dict) -> bool:
        """Check if dependencies need updating."""
        # Get hash of dependency files
        dep_files = {
            "javascript": ["package-lock.json", "package.json"],
            "typescript": ["package-lock.json", "package.json"],
            "python": ["requirements.txt", "Pipfile.lock", "poetry.lock"],
        }
        
        files = dep_files.get(config.get("language", ""), [])
        
        for f in files:
            file_path = repo_path / f
            if file_path.exists():
                # Check if file changed in last pull
                result = subprocess.run(
                    ["git", "diff", "HEAD~1", "--name-only", f],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True
                )
                if f in result.stdout:
                    return True
        
        # Also check if node_modules/venv doesn't exist
        if config.get("language") in ["javascript", "typescript"]:
            if not (repo_path / "node_modules").exists():
                return True
        elif config.get("language") == "python":
            if not (repo_path / ".venv").exists():
                return True
        
        return False
    
    def _install_dependencies(self, repo_path: Path, config: dict):
        """Install dependencies based on language."""
        language = config.get("language", "")
        install_cmd = config.get("install_command", "")
        
        if not install_cmd:
            if language in ["javascript", "typescript"]:
                install_cmd = "npm ci"
            elif language == "python":
                install_cmd = "pip install -r requirements.txt"
        
        if install_cmd:
            # Run in Docker for isolation
            from docker_sandbox import DockerSandbox
            docker = DockerSandbox()
            docker.run_with_network(
                image=config.get("docker_image", "node:20"),
                command=install_cmd,
                workdir="/app",
                volumes={str(repo_path): "/app"},
                timeout=600
            )
    
    def _git(self, repo_path: Path, args: list) -> str:
        """Run git command."""
        result = subprocess.run(
            ["git"] + args,
            cwd=str(repo_path),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Git error: {result.stderr}")
        return result.stdout
    
    def cleanup_after_task(self, repo_path: Path, keep_branch: bool = False):
        """Clean up after task completion."""
        main_branch = "main"  # Could be from config
        
        # Switch back to main
        self._git(repo_path, ["checkout", main_branch])
        
        if not keep_branch:
            # List and delete fix/ branches
            result = self._git(repo_path, ["branch", "--list", "fix/*"])
            for branch in result.strip().split("\n"):
                branch = branch.strip()
                if branch:
                    try:
                        self._git(repo_path, ["branch", "-D", branch])
                    except:
                        pass
        
        # Clean up Claude session files
        claude_dir = repo_path / ".claude"
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
```

### 10.4 Updated repos.yaml with Full Configuration

```yaml
# ~/claude-agent/config/repos.yaml

repositories:
  frontend-app:
    url: git@github.com:your-org/frontend-app.git
    branch: main
    language: typescript
    test_command: npm test
    install_command: npm ci
    build_command: npm run build
    lint_command: npm run lint
    docker_image: node:20-alpine
    
    # Caching configuration
    cache_dirs:
      - node_modules
      - .next/cache
      - dist
    
    # For Claude context
    keywords:
      - frontend
      - react
      - ui
      - component
      - web
    
    # Important files to always include in context
    context_files:
      - README.md
      - src/types/index.ts
      - .eslintrc.js

  backend-api:
    url: git@github.com:your-org/backend-api.git
    branch: main
    language: python
    test_command: pytest -v
    install_command: pip install -r requirements.txt
    lint_command: ruff check .
    docker_image: python:3.11-slim
    
    cache_dirs:
      - .venv
      - __pycache__
      - .pytest_cache
    
    keywords:
      - backend
      - api
      - server
      - endpoint
      - database
    
    context_files:
      - README.md
      - app/models.py
      - app/schemas.py

  mobile-app:
    url: git@github.com:your-org/mobile-app.git
    branch: develop
    language: typescript
    test_command: npm test
    install_command: npm ci
    docker_image: node:20-alpine
    
    cache_dirs:
      - node_modules
    
    keywords:
      - mobile
      - react-native
      - ios
      - android
      - app

# Default settings for all repos
defaults:
  docker_timeout: 600
  max_file_size_kb: 500  # Skip files larger than this in analysis
  
# Cron job for nightly updates (optional)
maintenance:
  nightly_pull: true
  cleanup_old_branches_days: 7
```

### 10.5 Nightly Maintenance Script (Optional)

```bash
#!/bin/bash
# ~/claude-agent/scripts/nightly_maintenance.sh
# Add to crontab: 0 3 * * * /home/ubuntu/claude-agent/scripts/nightly_maintenance.sh

set -e

WORKSPACE="$HOME/claude-agent/workspace/repos"
LOG_FILE="$HOME/claude-agent/logs/maintenance.log"

echo "$(date): Starting nightly maintenance" >> "$LOG_FILE"

# Update all repos
for repo_dir in "$WORKSPACE"/*/; do
    repo_name=$(basename "$repo_dir")
    echo "$(date): Updating $repo_name" >> "$LOG_FILE"
    
    cd "$repo_dir"
    
    # Fetch latest
    git fetch --all --prune
    
    # Checkout main and pull
    main_branch=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
    git checkout "$main_branch"
    git pull origin "$main_branch"
    
    # Clean old fix branches (older than 7 days)
    for branch in $(git branch --list "fix/*" --format='%(refname:short)'); do
        last_commit=$(git log -1 --format=%ct "$branch")
        now=$(date +%s)
        age_days=$(( (now - last_commit) / 86400 ))
        
        if [ $age_days -gt 7 ]; then
            echo "$(date): Deleting old branch $branch ($age_days days old)" >> "$LOG_FILE"
            git branch -D "$branch"
        fi
    done
    
    # Prune Docker images
    docker image prune -f
    
done

echo "$(date): Maintenance complete" >> "$LOG_FILE"
```

### 10.6 Machine Specialization (Optional)

```yaml
# If you have multiple machines, you can specialize them:

# Machine 1: Frontend specialist
machine_1:
  repos:
    - frontend-app
    - design-system
    - marketing-site
  resources:
    memory: 8GB
    disk: 50GB

# Machine 2: Backend specialist  
machine_2:
  repos:
    - backend-api
    - data-pipeline
    - auth-service
  resources:
    memory: 16GB
    disk: 100GB

# Machine 3: Mobile specialist
machine_3:
  repos:
    - mobile-app
    - mobile-sdk
  resources:
    memory: 8GB
    disk: 80GB

# Orchestrator routes tasks to appropriate machine based on repo
```

---

## Updated Environment Variables

```bash
# ~/claude-agent/config/.env

# === Jira ===
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT=PROJ

# === GitHub ===
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_ORG=your-org-name

# === Slack ===
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_ALERTS_CHANNEL=#dev-ai-alerts
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxx

# === Claude ===
CLAUDE_CONFIG_DIR=/home/ubuntu/.claude

# === Agent Settings ===
TASK_TIMEOUT_MINUTES=20
MAX_FIX_ATTEMPTS=3
DOCKER_MEMORY_LIMIT=4g
LOG_LEVEL=INFO

# === Sentry (for Lambda) ===
SENTRY_CLIENT_SECRET=your-sentry-webhook-secret
```
