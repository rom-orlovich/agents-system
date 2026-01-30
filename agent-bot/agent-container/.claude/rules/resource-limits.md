# Resource Limits

## Enforcement Level
HIGH - Must be enforced to ensure system stability

## Core Principle
Respect resource constraints to maintain system performance and cost efficiency.

## Time Limits

### Per Task Type
- **Code Review:** 5 minutes
- **Bug Fix:** 10 minutes
- **Test Generation:** 5 minutes
- **Refactoring:** 15 minutes
- **Explanation:** 2 minutes
- **Default:** 10 minutes

### Enforcement
```python
TASK_TIMEOUTS = {
    "review": 300,
    "fix": 600,
    "test": 300,
    "refactor": 900,
    "explain": 120,
    "default": 600,
}
```

### Warnings
- **80%:** Warn user, suggest scope reduction
- **100%:** Trigger on-timeout hook

## Memory Limits

### Per Container
- **Maximum:** 4 GB
- **Reserved:** 2 GB
- **Warning threshold:** 3.2 GB (80%)

### Per Task
- **Typical:** 256 MB
- **Large repos:** 512 MB
- **Kill threshold:** 1 GB

### Enforcement
```python
if memory_usage > MEMORY_LIMIT:
    gracefully_shutdown()
    save_partial_results()
    notify_user("out of memory")
```

## Disk Limits

### Repository Storage
- **Total:** 100 GB
- **Per repo:** 500 MB max
- **Per organization:** 10 GB max

### Cleanup Rules
- Delete repos not accessed in 24 hours
- Clean temp files after each task
- Rotate logs older than 7 days

## API Rate Limits

### Claude API
- **Requests per minute:** 60
- **Tokens per day:** 1,000,000
- **Concurrent requests:** 5

### GitHub API
- **Per installation:** 5,000 requests/hour
- **Secondary rate limit:** 100 content creations/hour
- **Burst:** 20 requests/minute

### Other Services
- **Jira:** 100 requests/minute
- **Slack:** 1 request/second (tier-dependent)
- **Sentry:** 100 requests/minute

## Concurrency Limits

### Task Workers
- **Max concurrent tasks:** 10
- **Per organization:** 2
- **Queue size:** 1000 tasks

### Database Connections
- **Pool size:** 20
- **Max overflow:** 10
- **Timeout:** 30 seconds

### File Operations
- **Max open files:** 1024
- **Concurrent reads:** 50
- **Concurrent writes:** 10

## Token Limits

### Claude Models
```python
MODEL_LIMITS = {
    "claude-opus-4": {
        "context": 200_000,
        "output": 4_096
    },
    "claude-sonnet-4": {
        "context": 200_000,
        "output": 8_192
    },
    "claude-haiku-3": {
        "context": 200_000,
        "output": 4_096
    }
}
```

### Cost Controls
- **Per task budget:** $1.00
- **Per organization daily:** $100.00
- **Alert threshold:** $50.00/day
- **Hard limit:** $200.00/day

## File Size Limits

### Reading
- **Max file size:** 10 MB
- **Total files per task:** 100
- **Line limit per file:** 10,000

### Writing
- **Max log file:** 100 MB
- **Max result size:** 1 MB
- **Max commit size:** 50 MB

## Network Limits

### Request Timeouts
- **GitHub API:** 30 seconds
- **Webhook processing:** 10 seconds
- **MCP calls:** 60 seconds
- **Repository clone:** 300 seconds

### Bandwidth
- **Max download:** 100 MB/minute
- **Max upload:** 50 MB/minute

## Monitoring & Enforcement

### Real-Time Monitoring
```python
@dataclass
class ResourceUsage:
    cpu_percent: float
    memory_mb: int
    disk_mb: int
    network_mb: int
    open_files: int
    active_tasks: int
```

### Thresholds
```python
THRESHOLDS = {
    "cpu": 80,        # percent
    "memory": 3200,   # MB
    "disk": 80000,    # MB
    "tasks": 8,       # count
}
```

### Actions on Threshold Breach
1. **Warning (80%):** Log warning, alert ops
2. **Critical (90%):** Stop new tasks, alert urgently
3. **Emergency (95%):** Kill oldest tasks, emergency alert

## Cost Tracking

### Per Request
```python
@dataclass
class CostMetrics:
    task_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_seconds: float
```

### Aggregation
- Per task
- Per hour
- Per day
- Per organization
- Per integration

### Alerts
- **Daily spend > $50:** Warning
- **Daily spend > $100:** Critical
- **Sudden spike:** Anomaly detection
- **Single task > $1:** Flag for review

## Queue Management

### Priority Levels
```python
PRIORITY = {
    "critical": 0,   # Security issues
    "high": 1,       # Bug fixes
    "normal": 2,     # Reviews, tests
    "low": 3,        # Explanations
}
```

### Queue Limits
- **Max size:** 1000 tasks
- **Per organization:** 50 tasks
- **Backpressure:** Reject new tasks if queue > 80%

## Cleanup Strategies

### Automatic Cleanup
```python
async def cleanup_task():
    delete_temp_files(older_than=hours(1))
    delete_logs(older_than=days(7))
    delete_repos(not_accessed_in=hours(24))
    vacuum_database()
```

### Manual Cleanup (Emergency)
```python
async def emergency_cleanup():
    kill_longest_running_tasks(count=5)
    clear_queue(priority_below="high")
    force_gc_collection()
    restart_workers()
```

## Scaling Policies

### Horizontal Scaling
- **Scale up:** Queue length > 100
- **Scale down:** Queue empty for 5 minutes
- **Min workers:** 2
- **Max workers:** 20

### Vertical Scaling
- **Memory pressure:** Request larger instances
- **CPU pressure:** Add more workers

## Optimization Guidelines

### Reduce Resource Usage
1. Cache expensive operations
2. Limit file reads
3. Stream large responses
4. Use shallow git clones
5. Skip unnecessary indexing

### Reduce Cost
1. Use Haiku for simple tasks
2. Batch similar requests
3. Implement caching
4. Optimize prompts
5. Limit context size

## Emergency Procedures

### Out of Memory
1. Kill current task
2. Save partial results
3. Free memory
4. Restart worker
5. Notify ops

### Disk Full
1. Stop accepting new tasks
2. Clean old repos
3. Delete temp files
4. Alert ops
5. Increase disk or scale

### Cost Overrun
1. Pause non-critical tasks
2. Alert finance team
3. Review high-cost tasks
4. Implement stricter limits
5. Optimize or scale down
