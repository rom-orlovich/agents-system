---
name: slack-operations
description: Slack API operations for messages, channels, threads, and notifications. Use when posting messages to Slack, replying in threads, sending notifications, or managing Slack communications.
---

Slack operations using MCP tools for all API interactions.

## Quick Reference

- **Workflow**: See [flow.md](flow.md) for complete workflow guide and templates

## Key Principles

1. **Always use MCP tools** (`slack:post_message`) for API operations
2. **Reply in thread** using `thread_ts` when responding to messages
3. **Use rich blocks** for interactive notifications (approval buttons)
4. **Post responses** using MCP tools after task completion

## Environment

- `SLACK_BOT_TOKEN` - Slack bot token (xoxb-...)
- `SLACK_APP_TOKEN` - Slack app token (xapp-...) for socket mode

## MCP Operations

**Always use MCP tools for Slack API operations:**

- `slack:post_message` - Send messages, reply in threads, use rich blocks

See [flow.md](flow.md) for complete workflow examples.

## Response Posting

**IMPORTANT**: Always post responses after task completion using `slack:post_message`.

**For webhook tasks:** Always reply in thread using `thread_ts` from task metadata.

See [flow.md](flow.md) for workflow examples including job notifications and [templates.md](templates.md) for response templates.
