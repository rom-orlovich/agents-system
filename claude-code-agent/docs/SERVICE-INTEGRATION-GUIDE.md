# 🛠️ Service Integration & Webhook Guide

This guide provides step-by-step instructions for connecting external services (GitHub, Jira, Slack, Sentry) and custom webhooks to your Claude Code Agent system.

---

## 🏗️ 1. General Setup (Prerequisite)

Before configuring any service, you must ensure your agent is accessible from the internet.

### Expose your Local Server
Since you are likely running locally, use `ngrok` to create a public tunnel to your port `8000`.

1. **Start the tunnel**:
   ```bash
   make tunnel
   ```
2. **Copy the Public URL**: Look for the `Forwarding` URL (e.g., `https://a1b2-c3d4.ngrok-free.app`).
3. **Update `.env`**:
   Ensure your `.env` file has the public domain set:
   ```env
   WEBHOOK_PUBLIC_DOMAIN=https://a1b2-c3d4.ngrok-free.app
   ```

---

## 🐙 2. GitHub Integration

Connect GitHub to automate issue analysis, PR reviews, and bug fixing.

### Setup Steps
1. Navigate to your GitHub Repository → **Settings** → **Webhooks** → **Add webhook**.
2. **Payload URL**: `https://<YOUR_PUBLIC_DOMAIN>/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: Enter a secret (and update `GITHUB_WEBHOOK_SECRET` in your `.env`).
5. **Which events?**: Select **"Let me select individual events"** and check:
   - [x] **Issues** (Required for ticket-based analysis)
   - [x] **Issue comments** (Required for responding to `@agent` mentions)
   - [x] **Pull requests** (Required for PR reviews and implementation)
   - [x] **Pushes** (Optional - can trigger CI/CD analysis)
6. Click **Add webhook**.

### Available Commands
Use these by commenting on an issue or PR using the `@agent` prefix:
- `@agent analyze`: Provides a high-level analysis of the issue.
- `@agent plan`: Research and create a `PLAN.md` for the fix.
- `@agent fix`: Start the implementation flow (TDD) to resolve the issue.
- `@agent review`: Request a code review for a PR.

---

## 🎫 3. Jira Integration

Connect Jira to automatically process tickets and updates.

### Setup Steps
1. Go to **Jira Settings** (gear icon) → **System** → **WebHooks** (left sidebar).
2. Click **Create a WebHook**.
3. **Name**: `Claude Agent`
4. **URL**: `https://<YOUR_PUBLIC_DOMAIN>/webhooks/jira`
5. **Secret**: Enter a secret (and update `JIRA_WEBHOOK_SECRET` in your `.env`).
6. **Events**: Under "Issue", select:
   - [x] **Issue Created** (Triggers analysis upon creation)
   - [x] **Issue Updated** (Triggers when assignee changes to the AI Agent)
7. Click **Create**.

> [!NOTE]
> The agent primarily responds to Jira tickets when the **Assignee** is changed to the name specified in your `JIRA_AI_AGENT_NAME` env var (default is `AI Agent`).

### Available Commands
Add a comment to any Jira ticket:
- `@agent analyze`: Analyze the ticket requirements.
- `@agent plan`: Create an implementation plan.
- `@agent fix`: (Requires approval) Start implementing the solution.

---

## 💬 4. Slack Integration

Interact with your agent directly from Slack channels or via mentions.

### Setup Steps
1. Go to [Slack API: Your Apps](https://api.slack.com/apps) and click **Create New App**.
3. **Event Subscriptions**:
   - Enable Events.
   - **Request URL**: `https://<YOUR_PUBLIC_DOMAIN>/webhooks/slack`
   - Subscribe to Bot Events:
     - `app_mention`: Required for `@ClaudeAgent` mentions.
     - `message.channels`: Optional, allows agent to see messages in channels it is a member of.
4. **Interactivity**:
   - Enable **Interactivity**.
   - **Request URL**: `https://<YOUR_PUBLIC_DOMAIN>/webhooks/slack/interactivity`
   - This allows the agent to handle **Approve/Reject** button clicks for plans.
5. **Slash Commands**:
   - Create a command (e.g., `/agent`).
   - **Request URL**: `https://<YOUR_PUBLIC_DOMAIN>/webhooks/slack`
6. **Install App**: Install to your workspace and copy the **Signing Secret** to `SLACK_WEBHOOK_SECRET` in your `.env`.

### Usage
- **Mention**: `@ClaudeAgent what is the status of task #123?`
- **Command**: `/agent fix the login bug`

---

## 🔔 5. Sentry Integration

Automate error analysis when a new production error is captured.

### Setup Steps
1. In Sentry, go to **Settings** → **Projects** → [Your Project] → **Legacy Integrations** → **Webhooks**.
2. **Callback URL**: `https://<YOUR_PUBLIC_DOMAIN>/webhooks/sentry`
3. **Alert Rules**: Create an Alert Rule that triggers the webhook on:
   - [x] **A new issue is created** (Required)
   - [x] **Issue assigned** (Optional)
4. Update `SENTRY_WEBHOOK_SECRET` in your `.env` with the secret provided by Sentry.

### Automated Flow
- When a new error occurs, the **Planning Agent** will automatically:
  1. Analyze the stack trace.
  2. Locate the failing file in the codebase.
  3. Suggest a fix or create a task for the **Executor Agent**.

---

## ⚙️ 6. Custom Services

For any service not listed above, you can create a **Dynamic Webhook**.

### Via Dashboard (Easiest)
1. Open the Dashboard at `http://localhost:8000/dashboard`.
2. Go to the **Webhooks** tab.
3. Click **"New Webhook"**.
4. Define your **Provider Name** (e.g., `shopify`) and **Secret**.
5. Copy the generated URL: `https://<YOUR_DOMAIN>/webhooks/custom/<webhook_id>`.

### Configuration
You can define custom templates in the dashboard to map incoming JSON fields to agent prompts:
- **Trigger**: `order.created`
- **Template**: `New order received from {{customer.name}} for {{total_price}}. Please check inventory.`

---

## 💡 Pro Tips
- **Approval Flow**: Commands like `fix` usually require you to approve the task in the Dashboard before execution begins.
- **Logs**: Monitor incoming webhook payloads by running `make logs` to debug configuration issues.
- **Templates**: All webhooks use **Jinja2** templates. Use `{{payload.key}}` to access incoming data.
