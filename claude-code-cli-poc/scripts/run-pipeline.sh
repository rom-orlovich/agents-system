#!/bin/bash
# Run the full pipeline manually
# Usage: ./run-pipeline.sh <TICKET_ID>

set -e

TICKET_ID=${1:-""}

if [ -z "$TICKET_ID" ]; then
    echo "Usage: ./run-pipeline.sh <TICKET_ID>"
    echo "Example: ./run-pipeline.sh PROJ-123"
    exit 1
fi

echo "=== Running Pipeline for $TICKET_ID ==="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running"
    exit 1
fi

# Check if services are up
if ! docker compose ps | grep -q "running"; then
    echo "Starting services..."
    docker compose up -d
    sleep 5
fi

# Queue the task
echo ">>> Queueing planning task..."
curl -X POST http://localhost:8000/jira-webhook \
    -H "Content-Type: application/json" \
    -d "{
        \"webhookEvent\": \"jira:issue_created\",
        \"issue\": {
            \"key\": \"$TICKET_ID\",
            \"fields\": {
                \"summary\": \"Manual test for $TICKET_ID\",
                \"description\": \"Test ticket created via run-pipeline.sh\",
                \"labels\": [\"AI-Fix\"],
                \"priority\": {\"name\": \"Medium\"}
            }
        }
    }"

echo ""
echo ">>> Task queued!"
echo ""
echo "Monitor progress with:"
echo "  docker compose logs -f planning-agent"
echo ""
echo "When planning is complete and PR is created,"
echo "approve it with '@agent approve' comment."
echo ""
