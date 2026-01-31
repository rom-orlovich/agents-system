# Task Logger Microservice

Dedicated service for structured task logging. Consumes task events from Redis stream and writes structured log files.

## Architecture

```
Task Worker → Redis Queue → Task Logger Microservice → File System
                   ↓
            (task events)
```

## Event Types

### Webhook Events

- `webhook:received` - Raw webhook payload received
- `webhook:validated` - Signature verified
- `webhook:matched` - Command matched
- `webhook:task_created` - Task queued

### Task Events

- `task:created` - Task metadata
- `task:started` - Execution begins
- `task:output` - Streaming agent output
- `task:user_input` - User responds to Claude's question
- `task:completed` - Final results + metrics
- `task:failed` - Errors

## Log Structure

Each task gets its own directory with structured logs:

```
/data/logs/tasks/{task_id}/
├── metadata.json              # Static: task metadata
├── 01-input.json             # Static: initial task input
├── 02-webhook-flow.jsonl     # Stream: webhook processing events
├── 03-agent-output.jsonl     # Stream: Claude output, thinking, tool calls
├── 03-user-inputs.jsonl      # Stream: user interactive inputs
└── 04-final-result.json      # Static: final results + metrics
```

## API Endpoints

- `GET /health` - Health check
- `GET /tasks/{task_id}/logs` - Retrieve task logs
- `GET /metrics` - Queue depth, processed count

## Environment Variables

```bash
REDIS_URL=redis://redis:6379/0
LOGS_DIR=/data/logs/tasks
REDIS_STREAM=task_events
REDIS_CONSUMER_GROUP=task-logger
MAX_BATCH_SIZE=10
PORT=8090
LOG_LEVEL=INFO
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python main.py
```

## Running with Docker

```bash
# Build and start
docker-compose up -d task-logger

# View logs
docker-compose logs -f task-logger

# Check health
curl http://localhost:8090/health

# Get task logs
curl http://localhost:8090/tasks/{task_id}/logs

# Get metrics
curl http://localhost:8090/metrics
```

## Testing

```bash
# Run tests
pytest tests/

# Run tests in container
make test-task-logger
```

## Monitoring

### Metrics to Track

- Queue depth (`task_events` stream length)
- Processing rate (events/second)
- Log file creation rate
- Failed event count
- Disk usage (/data/logs/tasks)

### Alerts

- Queue depth > 1000 events
- Processing lag > 30 seconds
- Failed events > 5% of total
- Disk usage > 80%

## Scaling

- Can scale horizontally (multiple consumers)
- Each consumer gets different tasks (consumer group)
- Logs stored on shared volume (EFS/NFS)

## Performance

- Atomic writes (temp file + rename)
- Batch JSONL appends
- Consumer group for load distribution
- Redis streams for reliable delivery
