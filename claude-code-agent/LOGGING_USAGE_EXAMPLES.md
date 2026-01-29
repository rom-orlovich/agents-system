# Structured Logging System - Usage Examples

## Quick Start

The structured logging system automatically captures logs for every task. No code changes needed in your workflows - it's integrated at the infrastructure level.

## Example: Webhook → Task → Logs

### 1. Webhook Triggers Task

```bash
# GitHub webhook receives: "@agent review this PR"
POST /webhooks/github/wh-abc123
```

**Logs Created Immediately:**
- `task-def456/metadata.json` - Basic task info
- `task-def456/02-webhook-flow.jsonl` - Webhook stages logged in real-time

### 2. Task Worker Processes

```bash
# Worker picks up task and executes
# Agent analyzes PR, writes response
```

**Logs Updated During Execution:**
- `task-def456/03-agent-output.jsonl` - Streaming output captured
- `task-def456/metadata.json` - Updated with model info

### 3. Task Completes

```bash
# Final result ready
```

**Logs Finalized:**
- `task-def456/04-final-result.json` - Success, cost, tokens, duration
- `task-def456/metadata.json` - Updated with completion time

## Real-World Example Output

### Complete Task Log Set

```bash
$ ls -la /data/logs/tasks/task-6b12155c8e76/
-rw-r--r-- 1 app app  245 Jan 29 08:48 metadata.json
-rw-r--r-- 1 app app  512 Jan 29 08:48 01-input.json
-rw-r--r-- 1 app app  387 Jan 29 08:48 02-webhook-flow.jsonl
-rw-r--r-- 1 app app 15.2K Jan 29 08:52 03-agent-output.jsonl
-rw-r--r-- 1 app app  423 Jan 29 08:52 04-final-result.json
```

### metadata.json
```json
{
  "task_id": "task-6b12155c8e76",
  "source": "webhook",
  "provider": "github",
  "created_at": "2024-01-29T08:48:15.983Z",
  "started_at": "2024-01-29T08:48:20.142Z",
  "status": "completed",
  "assigned_agent": "brain",
  "agent_type": "planning",
  "model": "claude-opus-4-5-20251101"
}
```

### 01-input.json
```json
{
  "message": "@agent review this code for security issues",
  "source_metadata": {
    "provider": "github",
    "event_type": "issue_comment.created",
    "webhook_id": "wh-82279351bc0d",
    "repo": "test-owner/test-repo",
    "issue_number": 123,
    "comment_id": 456,
    "comment_body": "@agent review this code for security issues"
  }
}
```

### 02-webhook-flow.jsonl
```jsonl
{"timestamp":"2024-01-29T08:48:15.982Z","stage":"received","provider":"github","event_type":"issue_comment.created","webhook_id":"wh-82279351bc0d"}
{"timestamp":"2024-01-29T08:48:15.983Z","stage":"command_matching","matched_count":1,"commands":["cmd-review-001"]}
{"timestamp":"2024-01-29T08:48:15.984Z","stage":"task_created","task_id":"task-6b12155c8e76","command":"cmd-review-001","agent":"brain"}
```

### 03-agent-output.jsonl
```jsonl
{"timestamp":"2024-01-29T08:48:20.142Z","type":"output","content":"[SYSTEM] Task task-6b12155c8e76 started at 2024-01-29T08:48:20.142Z\n"}
{"timestamp":"2024-01-29T08:48:20.143Z","type":"output","content":"[SYSTEM] Agent: brain | Model: claude-opus-4-5-20251101\n"}
{"timestamp":"2024-01-29T08:48:20.144Z","type":"output","content":"[SYSTEM] Starting Claude CLI...\n"}
{"timestamp":"2024-01-29T08:48:25.230Z","type":"output","content":"I'll review the code for security issues. Let me start by examining the files.\n"}
{"timestamp":"2024-01-29T08:48:27.445Z","type":"output","content":"Reading authentication module...\n"}
{"timestamp":"2024-01-29T08:48:35.678Z","type":"output","content":"Found potential SQL injection vulnerability in user input handling.\n"}
{"timestamp":"2024-01-29T08:48:40.234Z","type":"output","content":"Recommendation: Use parameterized queries instead of string concatenation.\n"}
{"timestamp":"2024-01-29T08:48:42.567Z","type":"output","content":"Security review complete. Created issue with findings.\n"}
```

### 04-final-result.json
```json
{
  "success": true,
  "result": "Security review completed. Found 1 critical issue (SQL injection) and 2 warnings. Details posted in comment.",
  "error": null,
  "metrics": {
    "cost_usd": 0.0847,
    "input_tokens": 3420,
    "output_tokens": 1256,
    "duration_seconds": 22.425
  },
  "completed_at": "2024-01-29T08:48:42.567Z"
}
```

## API Usage Examples

### Get Complete Task Logs

```bash
# Get all logs in one call
curl http://localhost:8000/api/tasks/task-6b12155c8e76/logs/full | jq

# Response structure:
{
  "metadata": { /* metadata.json content */ },
  "input": { /* 01-input.json content */ },
  "webhook_flow": [ /* 02-webhook-flow.jsonl as array */ ],
  "agent_output": [ /* 03-agent-output.jsonl as array */ ],
  "final_result": { /* 04-final-result.json content */ }
}
```

### Get Specific Log Files

```bash
# Just the metadata
curl http://localhost:8000/api/tasks/task-6b12155c8e76/logs/metadata | jq

# Just the agent output
curl http://localhost:8000/api/tasks/task-6b12155c8e76/logs/agent-output | jq

# Just the final result
curl http://localhost:8000/api/tasks/task-6b12155c8e76/logs/final-result | jq
```

## Analysis Examples

### Find Expensive Tasks

```bash
# Find tasks that cost more than $0.10
find /data/logs/tasks -name "04-final-result.json" -exec sh -c '
  cost=$(jq -r ".metrics.cost_usd" "$1")
  if [ "$(echo "$cost > 0.10" | bc)" -eq 1 ]; then
    task_id=$(basename $(dirname "$1"))
    echo "$task_id: \$$cost"
  fi
' _ {} \;

# Output:
# task-abc123: $0.234
# task-def456: $0.156
# task-ghi789: $0.421
```

### Track Webhook Response Times

```bash
# Calculate time from webhook received to task created
for dir in /data/logs/tasks/task-*; do
  task_id=$(basename $dir)

  # Extract timestamps from webhook flow
  received=$(jq -r 'select(.stage=="received") | .timestamp' $dir/02-webhook-flow.jsonl | head -1)
  created=$(jq -r 'select(.stage=="task_created") | .timestamp' $dir/02-webhook-flow.jsonl | head -1)

  if [ -n "$received" ] && [ -n "$created" ]; then
    # Convert to epoch and calculate diff
    r_epoch=$(date -d "$received" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$received" +%s 2>/dev/null)
    c_epoch=$(date -d "$created" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$created" +%s 2>/dev/null)

    if [ -n "$r_epoch" ] && [ -n "$c_epoch" ]; then
      diff=$((c_epoch - r_epoch))
      echo "$task_id: ${diff}ms webhook processing time"
    fi
  fi
done
```

### Generate Cost Report

```python
import json
from pathlib import Path
from datetime import datetime

# Analyze task logs
logs_dir = Path("/data/logs/tasks")
total_cost = 0
total_tasks = 0
failed_tasks = 0
total_duration = 0

for task_dir in logs_dir.glob("task-*"):
    result_file = task_dir / "04-final-result.json"
    if result_file.exists():
        with open(result_file) as f:
            result = json.load(f)

        total_tasks += 1
        total_cost += result["metrics"]["cost_usd"]
        total_duration += result["metrics"]["duration_seconds"]

        if not result["success"]:
            failed_tasks += 1

# Print report
print(f"📊 Task Execution Report")
print(f"Total Tasks: {total_tasks}")
print(f"Failed Tasks: {failed_tasks} ({failed_tasks/total_tasks*100:.1f}%)")
print(f"Total Cost: ${total_cost:.2f}")
print(f"Average Cost: ${total_cost/total_tasks:.4f}")
print(f"Average Duration: {total_duration/total_tasks:.1f}s")
```

### Monitor Agent Output Patterns

```bash
# Find common agent actions
cat /data/logs/tasks/*/03-agent-output.jsonl | \
  jq -r '.content' | \
  grep -E "Using|Reading|Writing|Creating" | \
  sort | uniq -c | sort -nr | head -10

# Output:
#   245 Using Read tool
#   189 Reading file...
#   134 Using Grep tool
#    87 Writing changes...
#    45 Using Bash tool
#    32 Creating new file
#    28 Using Edit tool
#    19 Using Write tool
#    12 Using Glob tool
#     8 Creating directory
```

### Debug Failed Tasks

```bash
# Find all failed tasks and their errors
find /data/logs/tasks -name "04-final-result.json" | while read file; do
  success=$(jq -r '.success' "$file")
  if [ "$success" = "false" ]; then
    task_id=$(basename $(dirname "$file"))
    error=$(jq -r '.error' "$file" | head -c 100)
    echo "❌ $task_id: $error..."
  fi
done
```

### Track Model Usage

```bash
# Count tasks by model
find /data/logs/tasks -name "metadata.json" | \
  xargs jq -r '.model' | \
  sort | uniq -c | sort -nr

# Output:
#   156 claude-opus-4-5-20251101
#    89 claude-sonnet-4-5-20250929
#    12 claude-haiku-4-5-20250929
```

## Integration Examples

### Slack Notification on High Cost

```python
import json
from pathlib import Path
import requests

SLACK_WEBHOOK = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
COST_THRESHOLD = 0.50

def check_and_notify():
    logs_dir = Path("/data/logs/tasks")

    for task_dir in logs_dir.glob("task-*"):
        result_file = task_dir / "04-final-result.json"
        if not result_file.exists():
            continue

        with open(result_file) as f:
            result = json.load(f)

        cost = result["metrics"]["cost_usd"]
        if cost > COST_THRESHOLD:
            # Get task details
            with open(task_dir / "metadata.json") as f:
                metadata = json.load(f)

            # Send Slack notification
            requests.post(SLACK_WEBHOOK, json={
                "text": f"⚠️ High cost task detected",
                "blocks": [{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Task:* {metadata['task_id']}\n*Cost:* ${cost:.2f}\n*Agent:* {metadata['assigned_agent']}\n*Model:* {metadata['model']}"
                    }
                }]
            })

check_and_notify()
```

### Export to CSV for Analysis

```python
import json
import csv
from pathlib import Path

logs_dir = Path("/data/logs/tasks")
output_csv = "task_metrics.csv"

with open(output_csv, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "task_id", "source", "provider", "agent", "model",
        "success", "cost_usd", "input_tokens", "output_tokens",
        "duration_seconds", "created_at", "completed_at"
    ])

    for task_dir in logs_dir.glob("task-*"):
        metadata_file = task_dir / "metadata.json"
        result_file = task_dir / "04-final-result.json"

        if not (metadata_file.exists() and result_file.exists()):
            continue

        with open(metadata_file) as f:
            metadata = json.load(f)
        with open(result_file) as f:
            result = json.load(f)

        writer.writerow([
            metadata["task_id"],
            metadata.get("source", ""),
            metadata.get("provider", ""),
            metadata["assigned_agent"],
            metadata["model"],
            result["success"],
            result["metrics"]["cost_usd"],
            result["metrics"]["input_tokens"],
            result["metrics"]["output_tokens"],
            result["metrics"]["duration_seconds"],
            metadata.get("created_at", ""),
            result.get("completed_at", "")
        ])

print(f"Exported to {output_csv}")
```

## Monitoring Dashboard Example

```python
from flask import Flask, jsonify
import json
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/metrics/summary')
def metrics_summary():
    logs_dir = Path("/data/logs/tasks")

    # Last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)

    stats = {
        "total_tasks": 0,
        "successful_tasks": 0,
        "failed_tasks": 0,
        "total_cost": 0,
        "total_tokens": 0,
        "avg_duration": 0,
        "tasks_by_provider": {},
        "tasks_by_model": {}
    }

    durations = []

    for task_dir in logs_dir.glob("task-*"):
        metadata_file = task_dir / "metadata.json"
        result_file = task_dir / "04-final-result.json"

        if not (metadata_file.exists() and result_file.exists()):
            continue

        with open(metadata_file) as f:
            metadata = json.load(f)

        # Check if recent
        created = datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))
        if created < cutoff:
            continue

        with open(result_file) as f:
            result = json.load(f)

        # Update stats
        stats["total_tasks"] += 1
        stats["total_cost"] += result["metrics"]["cost_usd"]
        stats["total_tokens"] += result["metrics"]["input_tokens"] + result["metrics"]["output_tokens"]
        durations.append(result["metrics"]["duration_seconds"])

        if result["success"]:
            stats["successful_tasks"] += 1
        else:
            stats["failed_tasks"] += 1

        # Group by provider
        provider = metadata.get("provider", "unknown")
        stats["tasks_by_provider"][provider] = stats["tasks_by_provider"].get(provider, 0) + 1

        # Group by model
        model = metadata["model"]
        stats["tasks_by_model"][model] = stats["tasks_by_model"].get(model, 0) + 1

    if durations:
        stats["avg_duration"] = sum(durations) / len(durations)

    return jsonify(stats)

if __name__ == '__main__':
    app.run(port=5000)
```

---

## Tips

1. **Use jq for JSON parsing** - It's fast and powerful for log analysis
2. **Archive old logs** - Compress logs older than 30 days to save space
3. **Monitor disk usage** - Each task uses ~10-100KB, plan accordingly
4. **Index for search** - Consider Elasticsearch for large-scale log search
5. **Backup critical logs** - Back up logs for important tasks to S3/storage

## Troubleshooting

### Logs not being created?

1. Check `TASK_LOGS_ENABLED=true` in config
2. Verify `/data/logs/tasks` directory exists and is writable
3. Check application logs for TaskLogger errors

### JSONL files empty?

1. Streaming might not be working - check output queue
2. Task might have failed immediately - check error logs

### API returns 404?

1. Verify task_id is correct
2. Check if log directory exists: `ls /data/logs/tasks/task-{id}`
3. Ensure settings.task_logs_dir is correctly configured

---

**System Status: PRODUCTION READY** ✅

All components tested and operational. Logs are being created for every task execution.
