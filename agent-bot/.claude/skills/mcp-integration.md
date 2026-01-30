# MCP Integration - Using Model Context Protocol Servers

## Purpose
Enable agents to use MCP (Model Context Protocol) servers for interacting with external services (GitHub, Jira, Slack, Sentry) with strict type safety.

## When to Use
- Agent needs to post GitHub PR comments
- Agent needs to add emoji reactions to PRs
- Agent needs to create/update Jira issues
- Agent needs to post Slack messages
- Agent needs to update Sentry issues

## Available MCP Servers

### GitHub MCP Server (`github-mcp-server`)

**Tools**:
1. `github_post_pr_comment` - Post comment on PR
2. `github_add_pr_reaction` - Add emoji reaction to PR

**Example Usage**:
```python
# Tool: github_post_pr_comment
{
  "owner": "org-name",
  "repo": "repo-name",
  "pr_number": 123,
  "comment": "LGTM! Tests passing ✅"
}

# Tool: github_add_pr_reaction
{
  "owner": "org-name",
  "repo": "repo-name",
  "pr_number": 123,
  "reaction": "+1"  # or: -1, laugh, hooray, confused, heart, rocket, eyes
}
```

### Jira MCP Server (`jira-mcp-server`)

**Tools**:
1. `jira_add_comment` - Add comment to issue
2. `jira_get_issue` - Get issue details
3. `jira_create_issue` - Create new issue
4. `jira_transition_issue` - Change issue status

**Example Usage**:
```python
# Tool: jira_add_comment
{
  "issue_key": "PROJ-123",
  "comment": "Issue analysis complete. Root cause identified."
}

# Tool: jira_create_issue
{
  "project_key": "PROJ",
  "summary": "Bug found in authentication flow",
  "description": "Detailed description here...",
  "issue_type": "Bug"
}
```

### Slack MCP Server (`slack-mcp-server`)

**Tools**:
1. `slack_post_message` - Post message to channel
2. `slack_update_message` - Update existing message
3. `slack_post_thread_reply` - Reply in thread

**Example Usage**:
```python
# Tool: slack_post_message
{
  "channel": "C1234567890",
  "text": "Task completed successfully!",
  "blocks": []  # Optional rich formatting
}
```

### Sentry MCP Server (`sentry-mcp-server`)

**Tools**:
1. `sentry_add_comment` - Add comment to issue
2. `sentry_update_status` - Update issue status
3. `sentry_get_issue` - Get issue details

**Example Usage**:
```python
# Tool: sentry_update_status
{
  "issue_id": "12345",
  "status": "resolved"  # or: ignored, unresolved
}
```

## MCP Communication Pattern

### 1. Identify Required Tool
Based on task, determine which MCP tool to use:
- PR review → `github_post_pr_comment` + `github_add_pr_reaction`
- Issue update → `jira_add_comment` or `jira_transition_issue`
- Notification → `slack_post_message`
- Error tracking → `sentry_add_comment` or `sentry_update_status`

### 2. Prepare Tool Arguments
Create strictly-typed arguments matching tool schema:
```python
from pydantic import BaseModel, ConfigDict

class PostPRCommentArgs(BaseModel):
    model_config = ConfigDict(strict=True)

    owner: str
    repo: str
    pr_number: int
    comment: str
```

### 3. Call MCP Tool
MCP servers are accessed via environment variables:
- `MCP_GITHUB_HOST` → GitHub MCP server
- `MCP_JIRA_HOST` → Jira MCP server
- `MCP_SLACK_HOST` → Slack MCP server
- `MCP_SENTRY_HOST` → Sentry MCP server

### 4. Handle Response
MCP tools return `list[TextContent]`:
```python
result = await mcp_client.call_tool(
    name="github_post_pr_comment",
    arguments=args.model_dump()
)

# result[0].text contains success message or error
if "Successfully posted" in result[0].text:
    # Success
else:
    # Handle error
```

## Error Handling

### Common Errors

**Authentication Error**:
```
Error: GITHUB_TOKEN not configured
```
→ Check environment variables are set

**Invalid Arguments**:
```
ValidationError: field required
```
→ Verify all required fields in tool arguments

**API Rate Limit**:
```
Error posting comment: 403 Forbidden (rate limit)
```
→ Implement retry with exponential backoff

**Network Error**:
```
Error: Connection timeout
```
→ Use circuit breaker pattern

## Best Practices

### Type Safety ✅
```python
# ✅ GOOD - Strict typing
class GitHubArgs(BaseModel):
    model_config = ConfigDict(strict=True)
    owner: str
    repo: str
    pr_number: int

# ❌ BAD - Loose typing
args = {"owner": owner, "repo": repo}  # No validation!
```

### Error Handling ✅
```python
# ✅ GOOD - Handle all cases
try:
    result = await mcp_client.call_tool(name, args)
    if "Error" in result[0].text:
        raise MCPToolError(result[0].text)
    return result[0].text
except MCPToolError as e:
    logger.error("mcp_tool_failed", tool=name, error=str(e))
    # Escalate or retry
```

### Logging ✅
```python
# ✅ GOOD - Log tool calls
logger.info(
    "mcp_tool_called",
    tool=name,
    provider="github",
    owner=args.owner,
    repo=args.repo,
    pr_number=args.pr_number
)
```

## Integration with Agents

### Agent Workflow

1. **Task Received**: Agent gets task from queue
2. **Analyze Task**: Determine required MCP tools
3. **Prepare Arguments**: Build strictly-typed args
4. **Call MCP Tools**: Execute via MCP client
5. **Process Results**: Handle success/failure
6. **Log Outcomes**: Record to task logger

### Example: PR Review Agent

```python
async def review_pr(task: Task):
    # 1. Extract PR info from task
    pr_number = task.source_metadata["pr_number"]
    owner, repo = task.source_metadata["repository"].split("/")

    # 2. Analyze PR (using other skills)
    analysis = await analyze_pr_code(owner, repo, pr_number)

    # 3. Prepare MCP arguments
    comment_args = PostPRCommentArgs(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        comment=analysis.to_markdown()
    )

    # 4. Post comment via MCP
    result = await github_mcp.call_tool(
        "github_post_pr_comment",
        comment_args.model_dump()
    )

    # 5. Add reaction based on quality
    reaction = "hooray" if analysis.quality_score > 8 else "eyes"
    reaction_args = AddPRReactionArgs(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        reaction=reaction
    )

    await github_mcp.call_tool(
        "github_add_pr_reaction",
        reaction_args.model_dump()
    )

    # 6. Log success
    task_logger.log_agent_output(
        "pr_review_completed",
        pr_number=pr_number,
        comment_posted=True,
        reaction_added=reaction
    )
```

## Testing MCP Integration

### Unit Tests
```python
@pytest.mark.asyncio
async def test_github_mcp_post_comment():
    # Mock MCP client
    mcp_client = MockMCPClient()

    args = PostPRCommentArgs(
        owner="test",
        repo="repo",
        pr_number=1,
        comment="Test comment"
    )

    result = await mcp_client.call_tool(
        "github_post_pr_comment",
        args.model_dump()
    )

    assert "Successfully posted" in result[0].text
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_full_pr_review_workflow():
    # Test complete workflow with real MCP server
    # (requires docker-compose up)
    task = create_pr_review_task()
    agent = PRReviewAgent(mcp_clients)

    result = await agent.execute(task)

    assert result.success is True
    assert result.comment_posted is True
    assert result.reaction_added is True
```

## Dependencies
- MCP servers running (docker-compose)
- Environment variables configured
- Task logger for recording operations
- Pydantic for strict type validation

## Related Skills
- `code-analysis` - Analyze PR code
- `security-scanning` - Check for vulnerabilities
- `task-logging` - Log MCP operations

## Escalation
Escalate to human when:
- MCP tool fails after 3 retries
- Authentication errors
- Rate limit exceeded
- Tool returns unexpected format
